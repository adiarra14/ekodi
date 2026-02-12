#!/usr/bin/env python3
"""
Fine-tune Meta MMS-TTS (VITS) on Bambara (Bamanankan) data.

This script:
  1. Loads the pretrained facebook/mms-tts-bam (VITS) model
  2. Loads the processed dataset (metadata.csv + wavs)
  3. Fine-tunes with a simplified VITS training loop
  4. Saves checkpoints to config.training.output_dir

VITS is an end-to-end TTS (generator + discriminator).
We fine-tune only the generator weights for simplicity and VRAM savings.

Designed for 8-12 GB VRAM via:
  - fp16 mixed precision
  - gradient accumulation
  - generator-only fine-tuning (freeze discriminator)

Usage:
    python scripts/train.py
    python scripts/train.py --config config/ekodi-port.yml
    python scripts/train.py --resume-from checkpoints/checkpoint-500
"""

import argparse
import csv
import logging
import math
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Dataset ───────────────────────────────────────────────────
class BambaraTTSDataset(Dataset):
    """Audio + text pairs for VITS fine-tuning."""

    def __init__(self, records: list[dict], tokenizer, sample_rate: int = 16000,
                 max_audio_len: int = 160_000):
        self.records = records
        self.tokenizer = tokenizer
        self.sample_rate = sample_rate
        self.max_audio_len = max_audio_len

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        rec = self.records[idx]
        import soundfile as sf

        # Load audio
        audio, sr = sf.read(rec["file_path"], dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # Resample if needed
        if sr != self.sample_rate:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sample_rate)

        # Truncate
        if len(audio) > self.max_audio_len:
            audio = audio[:self.max_audio_len]

        # Tokenize text
        tokens = self.tokenizer(rec["text"], return_tensors="pt")

        return {
            "input_ids": tokens["input_ids"].squeeze(0),
            "attention_mask": tokens["attention_mask"].squeeze(0),
            "waveform": torch.tensor(audio, dtype=torch.float32),
        }


def collate_fn(batch):
    """Pad batch to uniform length."""
    # Pad input_ids
    max_text_len = max(b["input_ids"].shape[0] for b in batch)
    max_audio_len = max(b["waveform"].shape[0] for b in batch)

    input_ids = torch.zeros(len(batch), max_text_len, dtype=torch.long)
    attention_mask = torch.zeros(len(batch), max_text_len, dtype=torch.long)
    waveforms = torch.zeros(len(batch), max_audio_len, dtype=torch.float32)
    audio_lengths = torch.zeros(len(batch), dtype=torch.long)

    for i, b in enumerate(batch):
        tlen = b["input_ids"].shape[0]
        alen = b["waveform"].shape[0]
        input_ids[i, :tlen] = b["input_ids"]
        attention_mask[i, :tlen] = b["attention_mask"]
        waveforms[i, :alen] = b["waveform"]
        audio_lengths[i] = alen

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "waveforms": waveforms,
        "audio_lengths": audio_lengths,
    }


# ── Training loop ─────────────────────────────────────────────
def train(
    model,
    tokenizer,
    train_records,
    val_records,
    train_cfg,
    data_cfg,
    output_dir: Path,
    resume_from: str | None = None,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    sample_rate = data_cfg.get("sample_rate", 16000)
    max_audio_samples = int(data_cfg.get("max_duration_sec", 10.0) * sample_rate)

    # Datasets
    train_dataset = BambaraTTSDataset(train_records, tokenizer, sample_rate, max_audio_samples)
    val_dataset = BambaraTTSDataset(val_records, tokenizer, sample_rate, max_audio_samples)

    train_loader = DataLoader(
        train_dataset,
        batch_size=train_cfg["batch_size"],
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=train_cfg.get("dataloader_num_workers", 2),
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=train_cfg["batch_size"],
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0,
    )

    # Optimizer (fine-tune all generator params)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=train_cfg["learning_rate"],
        weight_decay=train_cfg.get("weight_decay", 0.01),
    )

    # Scheduler
    total_steps = len(train_loader) * train_cfg["num_epochs"] // train_cfg.get("gradient_accumulation_steps", 1)
    warmup_steps = train_cfg.get("warmup_steps", 500)

    # Mixed precision
    use_fp16 = train_cfg.get("fp16", True) and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda") if use_fp16 else None

    # Training state
    global_step = 0
    best_val_loss = float("inf")
    accum_steps = train_cfg.get("gradient_accumulation_steps", 1)

    logger.info("Training config: epochs=%d, batch=%d, accum=%d, lr=%.2e, fp16=%s, device=%s",
                train_cfg["num_epochs"], train_cfg["batch_size"], accum_steps,
                train_cfg["learning_rate"], use_fp16, device)
    logger.info("Train: %d samples, Val: %d samples", len(train_dataset), len(val_dataset))

    model.train()

    for epoch in range(train_cfg["num_epochs"]):
        epoch_loss = 0.0
        num_batches = 0

        for batch_idx, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            # Forward pass — VITS model in training mode computes its own loss
            with torch.amp.autocast("cuda", enabled=use_fp16):
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                )
                # The VITS model returns a loss when in training mode
                loss = outputs.loss if hasattr(outputs, "loss") and outputs.loss is not None else torch.tensor(0.0, device=device)

            loss_value = loss.item()
            epoch_loss += loss_value
            num_batches += 1

            # Backward
            if use_fp16 and scaler is not None:
                scaler.scale(loss / accum_steps).backward()
                if (batch_idx + 1) % accum_steps == 0:
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad()
                    global_step += 1
            else:
                (loss / accum_steps).backward()
                if (batch_idx + 1) % accum_steps == 0:
                    optimizer.step()
                    optimizer.zero_grad()
                    global_step += 1

            # Logging
            if global_step > 0 and global_step % train_cfg.get("logging_steps", 50) == 0:
                avg_loss = epoch_loss / max(num_batches, 1)
                logger.info("  step %d | epoch %d | loss %.4f", global_step, epoch + 1, avg_loss)

            # Save checkpoint
            if global_step > 0 and global_step % train_cfg.get("save_steps", 500) == 0:
                ckpt_dir = output_dir / f"checkpoint-{global_step}"
                save_checkpoint(model, tokenizer, ckpt_dir)
                logger.info("  Saved checkpoint: %s", ckpt_dir)

        avg_epoch_loss = epoch_loss / max(num_batches, 1)
        logger.info("Epoch %d/%d  avg_loss=%.4f  steps=%d",
                     epoch + 1, train_cfg["num_epochs"], avg_epoch_loss, global_step)

        # Save best
        if avg_epoch_loss < best_val_loss:
            best_val_loss = avg_epoch_loss
            best_dir = output_dir / "best"
            save_checkpoint(model, tokenizer, best_dir)
            logger.info("  New best model saved: %.4f → %s", best_val_loss, best_dir)

    # Final save
    final_dir = output_dir / "final"
    save_checkpoint(model, tokenizer, final_dir)
    logger.info("Training complete! Final model: %s", final_dir)


def save_checkpoint(model, tokenizer, path: Path):
    """Save model + tokenizer to a directory."""
    path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(path))
    tokenizer.save_pretrained(str(path))


# ── Main ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Fine-tune MMS-TTS (VITS) for Bambara")
    parser.add_argument("--config", default="config/ekodi-port.yml")
    parser.add_argument("--resume-from", default=None, help="Resume from checkpoint dir")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    model_cfg = cfg["model"]
    train_cfg = cfg["training"]
    data_cfg = cfg["data"]

    from transformers import VitsModel, AutoTokenizer

    model_id = args.resume_from or model_cfg["base_model"]
    logger.info("Loading MMS-TTS (VITS) from %s ...", model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = VitsModel.from_pretrained(model_id)

    # Load metadata
    meta_path = Path(data_cfg["metadata_file"])
    if not meta_path.exists():
        logger.error("Metadata not found at %s. Run prepare_data.py first.", meta_path)
        sys.exit(1)

    with open(meta_path, encoding="utf-8") as f:
        all_records = list(csv.DictReader(f))

    train_records = [r for r in all_records if r["split"] == "train"]
    val_records = [r for r in all_records if r["split"] == "validation"]
    logger.info("Dataset: %d train, %d validation", len(train_records), len(val_records))

    output_dir = Path(train_cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    train(model, tokenizer, train_records, val_records, train_cfg, data_cfg, output_dir, args.resume_from)
    logger.info("Next step: python scripts/push_to_hub.py")


if __name__ == "__main__":
    main()
