#!/usr/bin/env python3
"""
Fine-tune MMS-TTS (VITS) for Bambara – Embedding & Duration Predictor adapter.

HuggingFace VitsModel is inference-first. We work around this by:
1. Running the model in eval mode (inference generates audio)
2. Computing mel-spectrogram loss between generated and target audio
3. Only updating embeddings + duration predictor weights

For full VITS training (with discriminator + KL loss), use the Colab notebook:
    notebooks/ekodi_vits_finetune.ipynb

Usage:
    python scripts/train.py
    python scripts/train.py --config config/ekodi-port.yml --epochs 5
"""

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def compute_mel(wav_tensor, sr=16000, n_fft=1024, hop=256, n_mels=80, device="cuda"):
    """Compute log-mel spectrogram."""
    import torchaudio.transforms as T
    mel_fn = T.MelSpectrogram(sample_rate=sr, n_fft=n_fft, hop_length=hop, n_mels=n_mels).to(device)
    return torch.log(mel_fn(wav_tensor).clamp(min=1e-5))


def mel_loss(pred_wav, target_wav, sr=16000, device="cuda"):
    """L1 + spectral convergence on mel-spectrograms."""
    min_len = min(pred_wav.shape[-1], target_wav.shape[-1])
    if min_len < 1024:
        return torch.tensor(0.0, device=device)
    p = compute_mel(pred_wav[..., :min_len], sr, device=device)
    t = compute_mel(target_wav[..., :min_len], sr, device=device)
    l1 = F.l1_loss(p, t)
    sc = torch.norm(t - p) / (torch.norm(t) + 1e-7)
    return l1 + sc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/ekodi-port.yml")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--max-samples", type=int, default=None,
                        help="Limit training samples (for quick tests)")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    model_cfg = cfg["model"]
    train_cfg = cfg["training"]
    data_cfg = cfg["data"]

    epochs = args.epochs or train_cfg.get("num_epochs", 5)
    lr = args.lr or train_cfg.get("learning_rate", 1e-4)
    batch_size = args.batch_size

    # ── Load model ──
    from transformers import VitsModel, AutoTokenizer
    model_id = model_cfg["base_model"]
    logger.info("Loading %s ...", model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = VitsModel.from_pretrained(model_id)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    sr = model.config.sampling_rate

    # ── Freeze strategy ──
    for p in model.parameters():
        p.requires_grad = False
    unfrozen_names = []
    for name, p in model.named_parameters():
        if any(k in name for k in ["embed_tokens", "duration_predictor", "proj"]):
            p.requires_grad = True
            unfrozen_names.append(name)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    logger.info("Trainable: %d / %d (%.1f%%)", trainable, total, 100 * trainable / total)

    if trainable == 0:
        logger.error("No trainable parameters!")
        sys.exit(1)

    # ── Load data ──
    meta_path = Path(data_cfg["metadata_file"])
    if not meta_path.exists():
        logger.error("Metadata not found: %s. Run prepare_data.py first.", meta_path)
        sys.exit(1)
    with open(meta_path, encoding="utf-8") as f:
        all_recs = list(csv.DictReader(f))
    train_recs = [r for r in all_recs if r["split"] == "train"]
    if args.max_samples:
        train_recs = train_recs[:args.max_samples]
    logger.info("Training on %d samples", len(train_recs))

    # ── Optimizer ──
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=0.01
    )

    output_dir = Path(train_cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    best_loss = float("inf")

    logger.info("Training: epochs=%d, lr=%.1e, device=%s", epochs, lr, device)

    # ── Training ──
    for epoch in range(epochs):
        model.train()  # Set train mode (grads flow through unfrozen params)
        t0 = time.time()
        epoch_loss = 0.0
        n_ok = 0

        for i, rec in enumerate(train_recs):
            try:
                # Load target audio
                audio, _ = sf.read(rec["file_path"], dtype="float32")
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)
                max_len = int(5.0 * sr)  # Cap at 5 seconds for VRAM
                if len(audio) > max_len:
                    audio = audio[:max_len]
                target = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).to(device)

                # Tokenize
                tokens = tokenizer(rec["text"], return_tensors="pt").to(device)

                # Forward
                output = model(**tokens)
                pred = output.waveform  # (1, T)

                # Loss
                loss = mel_loss(pred, target, sr, device)

                if torch.isnan(loss) or loss.item() == 0:
                    continue

                loss.backward()
                epoch_loss += loss.item()
                n_ok += 1

                # Step every batch_size samples
                if n_ok % batch_size == 0:
                    torch.nn.utils.clip_grad_norm_(
                        [p for p in model.parameters() if p.requires_grad], 1.0
                    )
                    optimizer.step()
                    optimizer.zero_grad()

                if n_ok % 100 == 0:
                    logger.info("  [%d/%d] loss=%.4f (%.1fs)", n_ok, len(train_recs),
                                loss.item(), time.time() - t0)

            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                optimizer.zero_grad()
                continue
            except Exception as e:
                if i < 5:
                    logger.warning("  Sample %d error: %s", i, e)
                continue

        avg = epoch_loss / max(n_ok, 1)
        dt = time.time() - t0
        logger.info("Epoch %d/%d  loss=%.4f  samples=%d/%d  time=%.0fs",
                     epoch + 1, epochs, avg, n_ok, len(train_recs), dt)

        if avg < best_loss and n_ok > 0:
            best_loss = avg
            model.save_pretrained(str(output_dir / "best"))
            tokenizer.save_pretrained(str(output_dir / "best"))
            logger.info("  -> Best model saved (loss=%.4f)", best_loss)

    # Final save
    model.save_pretrained(str(output_dir / "final"))
    tokenizer.save_pretrained(str(output_dir / "final"))
    logger.info("Done! Best loss: %.4f. Models at %s", best_loss, output_dir)


if __name__ == "__main__":
    main()
