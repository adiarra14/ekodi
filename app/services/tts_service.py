"""
Ekodi – TTS service (Meta MMS-TTS for Bambara).
"""

import base64
import hashlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure tts/ is on sys.path so we can import src.model
_tts_root = Path(__file__).resolve().parent.parent.parent / "tts"
if str(_tts_root) not in sys.path:
    sys.path.insert(0, str(_tts_root))

_tts_model = None
_audio_cache: dict[str, bytes] = {}
CACHE_SIZE = 128


def get_tts():
    """Lazy-load TTS model."""
    global _tts_model
    if _tts_model is None:
        from app.config import get_settings
        from src.model import EkodiTTS

        settings = get_settings()
        _tts_model = EkodiTTS.from_config(settings.TTS_CONFIG_PATH)
        logger.info("MMS-TTS model loaded")
    return _tts_model


def synthesize_to_b64(text: str) -> str | None:
    """Synthesize text with MMS-TTS, return base64 WAV."""
    try:
        tts = get_tts()
        wav = tts.synthesize(text, speaker="ekodi")
        from src.audio_utils import audio_to_bytes
        wav_bytes = audio_to_bytes(wav, sr=tts.sample_rate)
        return base64.b64encode(wav_bytes).decode("ascii")
    except Exception as e:
        logger.warning("TTS synthesis failed: %s", e)
        return None


def synthesize_to_wav(text: str, speaker: str = "ekodi") -> bytes:
    """Synthesize text → WAV bytes (with cache)."""
    key = hashlib.sha256(f"{speaker}::{text}".encode()).hexdigest()
    if key in _audio_cache:
        return _audio_cache[key]

    model = get_tts()
    wav = model.synthesize(text, speaker=speaker)
    from src.audio_utils import audio_to_bytes
    wav_bytes = audio_to_bytes(wav, sr=model.sample_rate)

    if len(_audio_cache) >= CACHE_SIZE:
        del _audio_cache[next(iter(_audio_cache))]
    _audio_cache[key] = wav_bytes
    return wav_bytes
