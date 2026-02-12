#!/usr/bin/env python3
"""
Convert custom Bambara .m4a voice samples to 16 kHz mono .wav files
and create a transcription template CSV for the user to fill in.

Uses imageio-ffmpeg (bundled ffmpeg binary, no system install needed).

Usage:
    python scripts/convert_voice_samples.py
"""

import csv
import logging
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

VOICE_DIR = Path("assets/voice")
OUTPUT_DIR = Path("data/custom_voice")
TARGET_SR = 16000


def get_ffmpeg_path():
    """Get ffmpeg binary path from imageio-ffmpeg."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        # Try system ffmpeg
        return "ffmpeg"


def convert_m4a_to_wav(m4a_path: Path, wav_path: Path, ffmpeg_bin: str) -> bool:
    """Convert .m4a to 16kHz mono .wav using ffmpeg."""
    try:
        cmd = [
            ffmpeg_bin,
            "-y",               # overwrite
            "-i", str(m4a_path),
            "-ar", str(TARGET_SR),
            "-ac", "1",         # mono
            "-sample_fmt", "s16",
            "-f", "wav",
            str(wav_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            logger.warning("  ffmpeg error for %s: %s", m4a_path.name, result.stderr[-200:])
            return False
        return wav_path.exists() and wav_path.stat().st_size > 1000
    except Exception as e:
        logger.warning("  Conversion failed for %s: %s", m4a_path.name, e)
        return False


def get_audio_duration(wav_path: Path) -> float:
    """Get duration of a wav file in seconds."""
    try:
        info = sf.info(str(wav_path))
        return info.duration
    except Exception:
        return 0.0


def main():
    if not VOICE_DIR.exists():
        logger.error("Voice directory not found: %s", VOICE_DIR)
        sys.exit(1)

    m4a_files = sorted(VOICE_DIR.glob("*.m4a"))
    if not m4a_files:
        logger.error("No .m4a files found in %s", VOICE_DIR)
        sys.exit(1)

    logger.info("Found %d .m4a files in %s", len(m4a_files), VOICE_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_path()
    logger.info("Using ffmpeg: %s", ffmpeg_bin)

    results = []
    for m4a in m4a_files:
        wav_name = m4a.stem + ".wav"
        wav_path = OUTPUT_DIR / wav_name

        logger.info("  Converting %s ...", m4a.name)
        if convert_m4a_to_wav(m4a, wav_path, ffmpeg_bin):
            dur = get_audio_duration(wav_path)
            # Extract a readable description from the filename
            desc = m4a.stem.replace("bm-", "").replace("-", " ").strip()
            results.append({
                "file_path": str(wav_path),
                "original_file": m4a.name,
                "description": desc,
                "duration_sec": f"{dur:.1f}",
                "text": "",  # <-- USER FILLS THIS IN
            })
            logger.info("    -> %s (%.1fs)", wav_path, dur)
        else:
            logger.warning("    FAILED: %s", m4a.name)

    if not results:
        logger.error("No files converted!")
        sys.exit(1)

    # Save transcription template
    template_path = OUTPUT_DIR / "transcriptions.csv"
    with open(template_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "file_path", "original_file", "description", "duration_sec", "text"
        ])
        writer.writeheader()
        writer.writerows(results)

    logger.info("\n" + "=" * 60)
    logger.info("Converted %d / %d files to WAV", len(results), len(m4a_files))
    logger.info("WAV files saved to: %s", OUTPUT_DIR)
    logger.info("Transcription template: %s", template_path)
    logger.info("")
    logger.info("NEXT STEP: Open %s and fill in the 'text' column", template_path)
    logger.info("with the Bambara text spoken in each audio file.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
