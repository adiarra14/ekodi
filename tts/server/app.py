#!/usr/bin/env python3
"""
Ekodi Bambara TTS – FastAPI inference server + voice platform UI.

Endpoints:
    GET  /              → Voice platform web interface
    POST /tts           → synthesize Bambara text, returns WAV audio
    GET  /health        → health check
    GET  /speakers      → list available speakers

Usage:
    cd tts
    uvicorn server.app:app --host 0.0.0.0 --port 8000
    # or
    python server/app.py
"""

import hashlib
import logging
import sys
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "ekodi-port.yml"
SERVER_DIR = Path(__file__).resolve().parent


def load_config():
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


cfg = load_config()
srv_cfg = cfg.get("server", {})

# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="Ekodi Bambara TTS",
    description="Text-to-Speech API & Voice Platform for Bambara (Bamanankan)",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=srv_cfg.get("cors_origins", ["*"]),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files & Templates ─────────────────────────────────
app.mount("/static", StaticFiles(directory=str(SERVER_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(SERVER_DIR / "templates"))

# ── Global model (lazy loaded) ────────────────────────────────
_model = None


def get_model():
    global _model
    if _model is None:
        from src.model import EkodiTTS
        _model = EkodiTTS.from_config(str(CONFIG_PATH))
    return _model


# ── Simple LRU cache for repeated prompts ─────────────────────
_audio_cache: dict[str, bytes] = {}
CACHE_SIZE = srv_cfg.get("cache_size", 128)


def _cache_key(text: str, speaker: str) -> str:
    return hashlib.sha256(f"{speaker}::{text}".encode()).hexdigest()


# ── Request / Response models ─────────────────────────────────
class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000,
                      description="Bambara text to synthesize")
    speaker: str = Field(default="ekodi", description="Speaker name")


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool
    backend: str


class SpeakerResponse(BaseModel):
    speakers: list[str]


# ── Pages ─────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Serve the voice platform UI."""
    return templates.TemplateResponse("index.html", {"request": request})


# ── API Endpoints ─────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
def health():
    model = get_model()
    return HealthResponse(
        status="ok",
        model_loaded=model is not None,
        backend=model.backend if model else "none",
    )


@app.get("/speakers", response_model=SpeakerResponse)
def speakers():
    return SpeakerResponse(speakers=["ekodi"])


@app.post("/tts")
def synthesize(req: TTSRequest):
    """Synthesize Bambara text to speech. Returns WAV audio."""
    model = get_model()

    # Check cache
    key = _cache_key(req.text, req.speaker)
    if key in _audio_cache:
        logger.info("Cache hit for: %s", req.text[:50])
        return Response(
            content=_audio_cache[key],
            media_type="audio/wav",
            headers={"Content-Disposition": 'attachment; filename="ekodi_tts.wav"'},
        )

    try:
        wav_array = model.synthesize(req.text, speaker=req.speaker)
    except Exception as e:
        logger.error("Synthesis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {e}")

    # Convert to WAV bytes
    from src.audio_utils import audio_to_bytes
    wav_bytes = audio_to_bytes(wav_array, sr=model.sample_rate)

    # Cache (evict oldest if full)
    if len(_audio_cache) >= CACHE_SIZE:
        oldest_key = next(iter(_audio_cache))
        del _audio_cache[oldest_key]
    _audio_cache[key] = wav_bytes

    logger.info("Synthesized %d bytes for: %s", len(wav_bytes), req.text[:50])
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": 'attachment; filename="ekodi_tts.wav"'},
    )


# ── Standalone run ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.app:app",
        host=srv_cfg.get("host", "0.0.0.0"),
        port=srv_cfg.get("port", 8000),
        reload=False,
    )
