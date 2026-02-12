"""
Audio utilities for the Ekodi Bambara TTS pipeline.

Handles:
  - Resampling to target sample rate
  - Loudness normalisation
  - Silence trimming
  - Duration filtering
"""

import io
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    import librosa
except ImportError:
    librosa = None  # graceful fallback; resample won't work without it

try:
    import torchaudio
    _HAS_TORCHAUDIO = True
except ImportError:
    _HAS_TORCHAUDIO = False


TARGET_SR = 16_000       # MMS-TTS / VITS default
TARGET_PEAK_DB = -1.0    # peak normalisation target
SILENCE_THRESH_DB = -40  # for trimming
MIN_DURATION = 0.5       # seconds
MAX_DURATION = 10.0      # seconds


# ── Loading ───────────────────────────────────────────────────
def load_audio(path: str | Path, target_sr: int = TARGET_SR) -> tuple[np.ndarray, int]:
    """Load an audio file, resample to *target_sr*, return (waveform_1d, sr)."""
    audio, sr = sf.read(str(path), dtype="float32")
    # mono
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    # resample
    if sr != target_sr:
        if librosa is not None:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        else:
            raise RuntimeError("librosa is needed for resampling – pip install librosa")
        sr = target_sr
    return audio, sr


# ── Normalisation ─────────────────────────────────────────────
def peak_normalize(audio: np.ndarray, target_db: float = TARGET_PEAK_DB) -> np.ndarray:
    """Peak-normalise waveform to *target_db* dBFS."""
    peak = np.max(np.abs(audio))
    if peak < 1e-8:
        return audio
    target_peak = 10.0 ** (target_db / 20.0)
    return audio * (target_peak / peak)


# ── Trim silence ──────────────────────────────────────────────
def trim_silence(audio: np.ndarray, sr: int = TARGET_SR,
                 top_db: float = abs(SILENCE_THRESH_DB)) -> np.ndarray:
    """Trim leading/trailing silence."""
    if librosa is not None:
        trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
        return trimmed
    # basic fallback – find first/last sample above threshold
    threshold = 10.0 ** (-top_db / 20.0)
    mask = np.abs(audio) > threshold
    if not mask.any():
        return audio
    first = mask.argmax()
    last = len(mask) - mask[::-1].argmax()
    return audio[first:last]


# ── Duration filter ───────────────────────────────────────────
def is_valid_duration(audio: np.ndarray, sr: int = TARGET_SR,
                      min_sec: float = MIN_DURATION,
                      max_sec: float = MAX_DURATION) -> bool:
    dur = len(audio) / sr
    return min_sec <= dur <= max_sec


# ── Save ──────────────────────────────────────────────────────
def save_wav(audio: np.ndarray, path: str | Path, sr: int = TARGET_SR) -> None:
    sf.write(str(path), audio, sr, subtype="PCM_16")


def audio_to_bytes(audio: np.ndarray, sr: int = TARGET_SR, fmt: str = "WAV") -> bytes:
    """Return audio as in-memory bytes (for HTTP responses)."""
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format=fmt, subtype="PCM_16")
    buf.seek(0)
    return buf.read()


# ── Pipeline convenience ─────────────────────────────────────
def process_audio_file(
    path: str | Path,
    target_sr: int = TARGET_SR,
    trim: bool = True,
    normalize: bool = True,
) -> tuple[np.ndarray, int] | None:
    """Load → resample → trim → normalise.  Returns None if duration is invalid."""
    audio, sr = load_audio(path, target_sr)
    if trim:
        audio = trim_silence(audio, sr)
    if normalize:
        audio = peak_normalize(audio)
    if not is_valid_duration(audio, sr):
        return None
    return audio, sr
