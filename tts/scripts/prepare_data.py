#!/usr/bin/env python3
"""
Prepare Bambara TTS dataset for MMS-TTS (VITS) fine-tuning.

Reads the raw metadata CSV from download_data.py and produces:
  1. Normalised audio files (16 kHz, peak-normalised, silence-trimmed)
  2. Normalised text (Bambara text normalisation)
  3. Train / validation split
  4. Metadata CSV ready for training

Usage:
    python scripts/prepare_data.py
    python scripts/prepare_data.py --config config/ekodi-port.yml
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_utils import load_audio, peak_normalize, trim_silence, is_valid_duration, save_wav
from src.text_normalize import normalize_bambara


def main():
    parser = argparse.ArgumentParser(description="Prepare Bambara TTS data")
    parser.add_argument("--config", default="config/ekodi-port.yml")
    args = parser.parse_args()

    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    data_cfg = cfg["data"]

    raw_dir = Path(data_cfg["raw_dir"])
    processed_dir = Path(data_cfg["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    audio_out_dir = processed_dir / "wavs"
    audio_out_dir.mkdir(exist_ok=True)

    target_sr = data_cfg.get("sample_rate", 16000)
    min_dur = data_cfg.get("min_duration_sec", 0.5)
    max_dur = data_cfg.get("max_duration_sec", 10.0)
    val_ratio = data_cfg.get("val_ratio", 0.05)

    # Read raw metadata
    raw_meta = raw_dir / "raw_metadata.csv"
    if not raw_meta.exists():
        logger.error("Raw metadata not found at %s. Run download_data.py first.", raw_meta)
        sys.exit(1)

    with open(raw_meta, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    logger.info("Loaded %d raw records", len(rows))

    # Process each record
    processed_records = []
    for i, row in enumerate(rows):
        src_path = row["file_path"]
        text = row["text"]

        # Normalise text
        text_norm = normalize_bambara(text)
        if len(text_norm) < 2:
            continue

        # Process audio
        try:
            audio, sr = load_audio(src_path, target_sr)
            audio = trim_silence(audio, sr)
            audio = peak_normalize(audio)
        except Exception as e:
            logger.debug("Skipping %s: %s", src_path, e)
            continue

        if not is_valid_duration(audio, sr, min_dur, max_dur):
            continue

        # Save processed audio
        out_name = f"{i:06d}.wav"
        out_path = audio_out_dir / out_name
        save_wav(audio, out_path, sr)

        processed_records.append({
            "file_path": str(out_path),
            "text": text_norm,
            "speaker_id": row.get("speaker_id", "speaker_0"),
            "duration": round(len(audio) / sr, 3),
        })

    logger.info("Processed %d / %d records (%.1f%% kept)",
                len(processed_records), len(rows),
                100 * len(processed_records) / max(len(rows), 1))

    if not processed_records:
        logger.error("No valid records after processing!")
        sys.exit(1)

    # Train / val split
    np.random.seed(42)
    indices = np.random.permutation(len(processed_records))
    val_count = max(1, int(len(processed_records) * val_ratio))
    val_indices = set(indices[:val_count])

    train_records = []
    val_records = []
    for idx, rec in enumerate(processed_records):
        if idx in val_indices:
            rec["split"] = "validation"
            val_records.append(rec)
        else:
            rec["split"] = "train"
            train_records.append(rec)

    # Save metadata CSV
    meta_path = Path(data_cfg["metadata_file"])
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file_path", "text", "speaker_id", "duration", "split"])
        writer.writeheader()
        for rec in train_records + val_records:
            writer.writerow(rec)

    logger.info("Metadata saved: %s  (train=%d, val=%d)", meta_path, len(train_records), len(val_records))
    logger.info("Done! Next step: python scripts/train.py")


if __name__ == "__main__":
    main()
