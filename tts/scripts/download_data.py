#!/usr/bin/env python3
"""
Download open Bambara speech+text datasets for TTS fine-tuning.

Tries these sources (in order of preference):
  1. MALIBA-AI/bambara-asr-data   (HuggingFace – aligned Bambara audio+text)
  2. oza75/bambara-tts            (HuggingFace – community Bambara TTS data)
  3. Danube/bambara-tts           (HuggingFace – community Bambara TTS)
  4. mozilla-foundation/common_voice  (Bambara subset, if available)

Usage:
    python scripts/download_data.py                     # auto-detect best source
    python scripts/download_data.py --source maliba     # force specific source
    python scripts/download_data.py --config config/ekodi-port.yml
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Add parent dir to path so we can import src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def download_huggingface_dataset(dataset_id: str, subset: str | None, raw_dir: Path) -> list[dict]:
    """Download a HuggingFace dataset and return list of {audio_path, text, speaker}."""
    from datasets import load_dataset

    logger.info("Downloading %s (subset=%s) from HuggingFace ...", dataset_id, subset)
    try:
        if subset:
            ds = load_dataset(dataset_id, subset, split="train", trust_remote_code=True)
        else:
            ds = load_dataset(dataset_id, split="train", trust_remote_code=True)
    except Exception as e:
        logger.warning("Could not load %s: %s", dataset_id, e)
        return []

    logger.info("  → %d examples found", len(ds))

    records = []
    audio_dir = raw_dir / dataset_id.replace("/", "_")
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Figure out column names (datasets vary)
    cols = ds.column_names
    text_col = next((c for c in ["sentence", "text", "transcription", "transcript"] if c in cols), None)
    audio_col = next((c for c in ["audio", "path", "file"] if c in cols), None)

    if not text_col:
        logger.warning("  No text column found in %s (columns: %s). Skipping.", dataset_id, cols)
        return []

    for i, example in enumerate(ds):
        text = example.get(text_col, "")
        if not text or not text.strip():
            continue

        # Handle audio (HF datasets usually have {"array": ..., "sampling_rate": ..., "path": ...})
        audio_data = example.get(audio_col)
        if audio_data is None:
            continue

        out_path = audio_dir / f"{i:06d}.wav"

        if isinstance(audio_data, dict) and "array" in audio_data:
            import soundfile as sf
            import numpy as np
            arr = np.array(audio_data["array"], dtype=np.float32)
            sr = audio_data.get("sampling_rate", 16000)
            sf.write(str(out_path), arr, sr)
        elif isinstance(audio_data, str) and Path(audio_data).exists():
            import shutil
            shutil.copy2(audio_data, out_path)
        else:
            # Try to save bytes
            try:
                if isinstance(audio_data, dict) and "bytes" in audio_data and audio_data["bytes"]:
                    out_path.write_bytes(audio_data["bytes"])
                else:
                    continue
            except Exception:
                continue

        records.append({
            "file_path": str(out_path),
            "text": text.strip(),
            "speaker_id": example.get("speaker_id", example.get("client_id", "speaker_0")),
        })

    logger.info("  → %d usable examples saved to %s", len(records), audio_dir)
    return records


# ── Source registry ───────────────────────────────────────────
SOURCES = {
    "maliba": ("MALIBA-AI/bambara-asr-data", None),
    "oza75": ("oza75/bambara-tts", None),
    "danube": ("Danube/bambara-tts", None),
    "commonvoice": ("mozilla-foundation/common_voice_16_0", "bm"),
}


def try_all_sources(raw_dir: Path) -> list[dict]:
    """Try each source until we get data."""
    for name, (dataset_id, subset) in SOURCES.items():
        logger.info("Trying source: %s ...", name)
        records = download_huggingface_dataset(dataset_id, subset, raw_dir)
        if records:
            logger.info("SUCCESS: Got %d records from '%s'", len(records), name)
            return records
        logger.info("  source '%s' yielded no data, trying next...", name)
    return []


def save_raw_metadata(records: list[dict], raw_dir: Path) -> Path:
    """Save downloaded records as a CSV."""
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
    parser.add_argument("--config", default="config/ekodi-port.yml",
                        help="Path to config file")
    parser.add_argument("--raw-dir", default=None,
                        help="Override raw data directory")
    args = parser.parse_args()

    # Load config
    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    raw_dir = Path(args.raw_dir or cfg["data"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    if args.source:
        dataset_id, subset = SOURCES[args.source]
        records = download_huggingface_dataset(dataset_id, subset, raw_dir)
    else:
        records = try_all_sources(raw_dir)

    if not records:
        logger.error(
            "No Bambara data found from any source.\n"
            "You can provide your own data by placing WAV files in %s\n"
            "and creating a CSV with columns: file_path, text, speaker_id",
            raw_dir,
        )
        sys.exit(1)

    save_raw_metadata(records, raw_dir)
    logger.info("Done! Next step: python scripts/prepare_data.py")


if __name__ == "__main__":
    main()
