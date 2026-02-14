#!/usr/bin/env python3
"""
Download open Bambara speech+text datasets for TTS fine-tuning.

Uses HuggingFace datasets with soundfile-based audio decoding
(avoids torchcodec/FFmpeg dependency issues on Windows).

Tries these sources (in order of preference):
  1. OumarDicko/Bambara_AudioSynthetique_42K_V3  (42K synthetic Bambara, most downloaded)
  2. kalilouisangare/bambara-speech-kis-clean-split (clean Bambara speech)
  3. oza75/bambara-asr                            (Bambara ASR data)

Usage:
    python scripts/download_data.py
    python scripts/download_data.py --source oumar
    python scripts/download_data.py --max-samples 5000
"""

import argparse
import csv
import io
import logging
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def download_dataset(dataset_id: str, subset: str | None, raw_dir: Path,
                     max_samples: int = 50000) -> list[dict]:
    """Download a HF dataset, decode audio with soundfile, save WAVs."""
    from datasets import load_dataset, Audio

    logger.info("Downloading %s (subset=%s) ...", dataset_id, subset)
    try:
        kwargs = {"split": "train", "streaming": True}
        if subset:
            ds = load_dataset(dataset_id, subset, **kwargs)
        else:
            ds = load_dataset(dataset_id, **kwargs)

        # Disable automatic audio decoding — we'll handle it ourselves
        ds = ds.cast_column("audio", Audio(decode=False)) if "audio" in ds.column_names else ds
    except Exception as e:
        logger.warning("Could not load %s: %s", dataset_id, e)
        return []

    # Detect columns
    cols = ds.column_names
    logger.info("  Columns: %s", cols)
    text_col = next((c for c in ["sentence", "text", "transcription", "transcript"] if c in cols), None)
    audio_col = next((c for c in ["audio", "path", "file"] if c in cols), None)

    if not text_col:
        logger.warning("  No text column found (columns: %s). Skipping.", cols)
        return []
    if not audio_col:
        logger.warning("  No audio column found (columns: %s). Skipping.", cols)
        return []

    logger.info("  Using text='%s', audio='%s'", text_col, audio_col)

    audio_dir = raw_dir / dataset_id.replace("/", "_")
    audio_dir.mkdir(parents=True, exist_ok=True)

    records = []
    skipped = 0

    for i, example in enumerate(ds):
        if i >= max_samples:
            logger.info("  Reached max_samples=%d, stopping.", max_samples)
            break

        text = example.get(text_col, "")
        if not text or not text.strip():
            skipped += 1
            continue

        audio_data = example.get(audio_col)
        if audio_data is None:
            skipped += 1
            continue

        out_path = audio_dir / f"{i:06d}.wav"

        try:
            if isinstance(audio_data, dict):
                if "bytes" in audio_data and audio_data["bytes"]:
                    # Decode raw bytes with soundfile
                    audio_bytes = audio_data["bytes"]
                    arr, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
                    if arr.ndim > 1:
                        arr = arr.mean(axis=1)
                    sf.write(str(out_path), arr, sr, subtype="PCM_16")
                elif "array" in audio_data:
                    arr = np.array(audio_data["array"], dtype=np.float32)
                    sr = audio_data.get("sampling_rate", 16000)
                    sf.write(str(out_path), arr, sr, subtype="PCM_16")
                elif "path" in audio_data and audio_data["path"]:
                    # Path reference — bytes should be alongside
                    skipped += 1
                    continue
                else:
                    skipped += 1
                    continue
            elif isinstance(audio_data, str):
                skipped += 1
                continue
            else:
                skipped += 1
                continue
        except Exception as e:
            logger.debug("  Skipping %d: %s", i, e)
            skipped += 1
            continue

        records.append({
            "file_path": str(out_path),
            "text": text.strip(),
            "speaker_id": str(example.get("speaker_id", example.get("client_id", "speaker_0"))),
        })

        if (i + 1) % 500 == 0:
            logger.info("  ... processed %d examples (%d saved, %d skipped)", i + 1, len(records), skipped)

    logger.info("  Done: %d usable / %d skipped → %s", len(records), skipped, audio_dir)
    return records


# ── Source registry ───────────────────────────────────────────
SOURCES = {
    "oumar": ("OumarDicko/Bambara_AudioSynthetique_42K_V3", None),
    "kali": ("kalilouisangare/bambara-speech-kis-clean-split", None),
    "oza75": ("oza75/bambara-asr", None),
}


def try_all_sources(raw_dir: Path, max_samples: int) -> list[dict]:
    """Try each source until we get data."""
    for name, (dataset_id, subset) in SOURCES.items():
        logger.info("Trying source: %s ...", name)
        records = download_dataset(dataset_id, subset, raw_dir, max_samples)
        if records:
            logger.info("SUCCESS: Got %d records from '%s'", len(records), name)
            return records
        logger.info("  source '%s' yielded no data, trying next...", name)
    return []


def save_raw_metadata(records: list[dict], raw_dir: Path) -> Path:
    meta_path = raw_dir / "raw_metadata.csv"
    with open(meta_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file_path", "text", "speaker_id"])
        writer.writeheader()
        writer.writerows(records)
    logger.info("Raw metadata saved to %s  (%d rows)", meta_path, len(records))
    return meta_path


def main():
    parser = argparse.ArgumentParser(description="Download Bambara TTS data")
    parser.add_argument("--source", choices=list(SOURCES.keys()), default=None,
                        help="Force a specific data source")
    parser.add_argument("--config", default="config/tts-port.yml")
    parser.add_argument("--raw-dir", default=None)
    parser.add_argument("--max-samples", type=int, default=10000,
                        help="Max samples to download (default 10000)")
    args = parser.parse_args()

    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    raw_dir = Path(args.raw_dir or cfg["data"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    if args.source:
        dataset_id, subset = SOURCES[args.source]
        records = download_dataset(dataset_id, subset, raw_dir, args.max_samples)
    else:
        records = try_all_sources(raw_dir, args.max_samples)

    if not records:
        logger.error(
            "No Bambara data found from any source.\n"
            "You can provide your own data by placing WAV files in %s\n"
            "and creating a CSV with columns: file_path, text, speaker_id",
            raw_dir,
        )
        sys.exit(1)

    save_raw_metadata(records, raw_dir)
    logger.info("Done! %d samples ready. Next: python scripts/prepare_data.py", len(records))


if __name__ == "__main__":
    main()
