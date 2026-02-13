"""
Ekodi – ASR service (Whisper for French, MMS-ASR for Bambara).
"""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_asr_model = None
_asr_processor = None


def _ensure_ffmpeg():
    """Make sure ffmpeg is on PATH (uses imageio bundle on Windows)."""
    if shutil.which("ffmpeg"):
        return
    try:
        import imageio_ffmpeg
        ffmpeg_src = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = str(Path(ffmpeg_src).parent)
        ffmpeg_link = Path(ffmpeg_dir) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not ffmpeg_link.exists():
            try:
                os.link(str(ffmpeg_src), str(ffmpeg_link))
            except OSError:
                shutil.copy2(str(ffmpeg_src), str(ffmpeg_link))
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        logger.info("ffmpeg ready via imageio")
    except ImportError:
        logger.warning("ffmpeg not found and imageio_ffmpeg not installed")


def get_asr():
    """Meta MMS-ASR for Bambara (lazy loaded, runs on CPU)."""
    global _asr_model, _asr_processor
    if _asr_model is None:
        _ensure_ffmpeg()
        import torch  # noqa: F811
        from transformers import Wav2Vec2ForCTC, AutoProcessor

        model_id = "facebook/mms-1b-all"
        logger.info("Loading MMS-ASR for Bambara (%s)...", model_id)
        _asr_processor = AutoProcessor.from_pretrained(model_id)
        _asr_model = Wav2Vec2ForCTC.from_pretrained(model_id)
        _asr_processor.tokenizer.set_target_lang("bam")
        _asr_model.load_adapter("bam")
        _asr_model.eval()
        logger.info("MMS-ASR ready (Bambara)")
    return _asr_model, _asr_processor


def transcribe_bambara(audio_path: str) -> str:
    """Transcribe audio → Bambara text (Meta MMS-ASR)."""
    import torch
    import librosa

    _ensure_ffmpeg()
    model, processor = get_asr()
    waveform, _ = librosa.load(audio_path, sr=16_000, mono=True)
    inputs = processor(waveform, sampling_rate=16_000, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    ids = torch.argmax(logits, dim=-1)[0]
    return processor.decode(ids).strip()


def transcribe_french(audio_path: str) -> str:
    """Transcribe audio → French text (OpenAI Whisper API)."""
    from openai import OpenAI
    from app.config import get_settings

    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1", file=f, language="fr",
        )
    return result.text.strip()
