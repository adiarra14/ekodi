#!/usr/bin/env python3
"""
Ekodi Bambara Voice AI – FastAPI server.

Pipeline:
  User speaks French  → Whisper(fr) → GPT(fr) → translate→Bambara → MMS-TTS(bam)
  User speaks Bambara → MMS-ASR(bam) → translate→French → GPT(fr) → translate→Bambara → MMS-TTS(bam)

Endpoints:
    GET  /              → Web interface
    POST /voice-chat    → full pipeline: audio → AI → Bambara audio
    POST /chat          → text chat: text → AI → Bambara audio
    POST /tts           → synthesize Bambara text → WAV
    GET  /health        → health check
"""

import base64
import hashlib
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "ekodi-port.yml"
SERVER_DIR = Path(__file__).resolve().parent
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_config():
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


load_env()
cfg = load_config()
srv_cfg = cfg.get("server", {})

# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="Ekodi Bambara Voice AI",
    description="Interactive Voice AI for Bambara (Bamanankan)",
    version="0.4.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=srv_cfg.get("cors_origins", ["*"]),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(SERVER_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(SERVER_DIR / "templates"))

# ── Models (lazy loaded) ─────────────────────────────────────
_tts_model = None
_openai_client = None
_asr_model = None
_asr_processor = None
_nllb_model = None
_nllb_tokenizer = None


def _ensure_ffmpeg():
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
        logger.info("ffmpeg ready")
    except ImportError:
        pass


def get_tts():
    global _tts_model
    if _tts_model is None:
        from src.model import EkodiTTS
        _tts_model = EkodiTTS.from_config(str(CONFIG_PATH))
    return _tts_model


def get_asr():
    """Meta MMS-ASR for Bambara (runs on CPU)."""
    global _asr_model, _asr_processor
    if _asr_model is None:
        _ensure_ffmpeg()
        import torch
        from transformers import Wav2Vec2ForCTC, AutoProcessor
        model_id = "facebook/mms-1b-all"
        logger.info("Loading MMS-ASR for Bambara...")
        _asr_processor = AutoProcessor.from_pretrained(model_id)
        _asr_model = Wav2Vec2ForCTC.from_pretrained(model_id)
        _asr_processor.tokenizer.set_target_lang("bam")
        _asr_model.load_adapter("bam")
        _asr_model.eval()
        logger.info("MMS-ASR ready (Bambara)")
    return _asr_model, _asr_processor


def get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise HTTPException(503, "OPENAI_API_KEY not set in tts/.env")
        _openai_client = OpenAI(api_key=api_key)
        logger.info("OpenAI client ready")
    return _openai_client


def get_nllb():
    """Load Meta NLLB translation model (French ↔ Bambara)."""
    global _nllb_model, _nllb_tokenizer
    if _nllb_model is None:
        from transformers import AutoModelForSeq2SeqLM, NllbTokenizer
        model_id = "facebook/nllb-200-distilled-600M"
        logger.info("Loading NLLB translator (%s)...", model_id)
        _nllb_tokenizer = NllbTokenizer.from_pretrained(model_id)
        _nllb_model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
        _nllb_model.eval()
        logger.info("NLLB translator ready (French ↔ Bambara)")
    return _nllb_model, _nllb_tokenizer


# ── ASR Functions ─────────────────────────────────────────────
def transcribe_bambara(audio_path: str) -> str:
    """Transcribe audio → Bambara text (Meta MMS-ASR)."""
    import torch, librosa
    model, processor = get_asr()
    waveform, _ = librosa.load(audio_path, sr=16_000, mono=True)
    inputs = processor(waveform, sampling_rate=16_000, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    ids = torch.argmax(logits, dim=-1)[0]
    return processor.decode(ids).strip()


def transcribe_french(audio_path: str) -> str:
    """Transcribe audio → French text (OpenAI Whisper)."""
    client = get_openai()
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1", file=f, language="fr",
        )
    return result.text.strip()


# ── GPT Functions ─────────────────────────────────────────────

GPT_SYSTEM = """Tu es Ekodi, un assistant vocal IA amical pour les locuteurs bambara au Mali.

Règles:
- Réponds TOUJOURS en français clair et simple
- Sois chaleureux et respectueux, comme un ami malien
- Réponses COURTES (1-3 phrases) — c'est une conversation vocale
- Si l'utilisateur te salue, salue-le chaleureusement
- Tu aides avec: questions générales, culture malienne/bambara, traductions, conversation quotidienne
- Si le message est en bambara, comprends l'intention et réponds en français"""

def gpt_chat(session_id: str, user_message_fr: str) -> str:
    """Send French message to GPT, get French response."""
    client = get_openai()
    add_to_conversation(session_id, "user", user_message_fr)
    messages = [{"role": "system", "content": GPT_SYSTEM}]
    messages.extend(get_conversation(session_id))

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=200,
        temperature=0.6,
    )
    ai_text = response.choices[0].message.content.strip()
    add_to_conversation(session_id, "assistant", ai_text)
    return ai_text


def translate_to_bambara(french_text: str) -> str:
    """Translate French → Bambara using Meta NLLB."""
    model, tokenizer = get_nllb()
    tokenizer.src_lang = "fra_Latn"
    inputs = tokenizer(french_text, return_tensors="pt", max_length=256, truncation=True)
    import torch
    with torch.no_grad():
        tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids("bam_Latn"),
            max_new_tokens=256,
        )
    return tokenizer.decode(tokens[0], skip_special_tokens=True)


def translate_bambara_to_french(bambara_text: str) -> str:
    """Translate Bambara → French using Meta NLLB."""
    model, tokenizer = get_nllb()
    tokenizer.src_lang = "bam_Latn"
    inputs = tokenizer(bambara_text, return_tensors="pt", max_length=256, truncation=True)
    import torch
    with torch.no_grad():
        tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids("fra_Latn"),
            max_new_tokens=256,
        )
    return tokenizer.decode(tokens[0], skip_special_tokens=True)


def synthesize_to_b64(text: str) -> str | None:
    """Synthesize text with MMS-TTS, return base64 WAV."""
    try:
        tts = get_tts()
        wav = tts.synthesize(text, speaker="ekodi")
        from src.audio_utils import audio_to_bytes
        wav_bytes = audio_to_bytes(wav, sr=tts.sample_rate)
        return base64.b64encode(wav_bytes).decode("ascii")
    except Exception as e:
        logger.warning("TTS failed: %s", e)
        return None


# ── Conversation memory ───────────────────────────────────────
_conversations: dict[str, list] = {}
MAX_HISTORY = 10


def get_conversation(session_id: str) -> list:
    if session_id not in _conversations:
        _conversations[session_id] = []
    return _conversations[session_id]


def add_to_conversation(session_id: str, role: str, content: str):
    conv = get_conversation(session_id)
    conv.append({"role": role, "content": content})
    if len(conv) > MAX_HISTORY * 2:
        _conversations[session_id] = conv[-(MAX_HISTORY * 2):]


# ── Request models ────────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    speaker: str = Field(default="ekodi")


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    input_lang: str = Field(default="fr", description="'fr' or 'bm'")
    session_id: str = Field(default="default")


# ── Pages ─────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    model = get_tts()
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "backend": model.backend if model else "none",
        "openai_configured": bool(os.environ.get("OPENAI_API_KEY")),
    }


@app.get("/speakers")
def speakers():
    return {"speakers": ["ekodi"]}


# ── API: Voice Chat (main pipeline) ──────────────────────────
@app.post("/voice-chat")
async def voice_chat(
    audio: UploadFile = File(...),
    input_lang: str = Form(default="fr"),
    session_id: str = Form(default="default"),
):
    """
    Full voice pipeline:
      French  → Whisper(fr) → GPT(fr) → translate→Bambara → TTS
      Bambara → MMS-ASR(bam) → translate→French → GPT(fr) → translate→Bambara → TTS
    """
    suffix = "." + (audio.filename.split(".")[-1] if audio.filename else "webm")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # ── Step 1: Transcribe ────────────────────────────────
        if input_lang == "bm":
            user_text = transcribe_bambara(tmp_path)
            logger.info("ASR(bam): %s", user_text[:80])
            # Translate Bambara → French for GPT
            user_text_fr = translate_bambara_to_french(user_text) if user_text else ""
            logger.info("→ French: %s", user_text_fr[:80])
        else:
            user_text = transcribe_french(tmp_path)
            user_text_fr = user_text
            logger.info("ASR(fr): %s", user_text[:80])
    except Exception as e:
        logger.error("ASR failed: %s", e)
        raise HTTPException(500, f"Transcription failed: {e}")
    finally:
        os.unlink(tmp_path)

    if not user_text:
        return JSONResponse({
            "user_text": "", "user_text_fr": "",
            "ai_text_fr": "", "ai_text_bm": "",
            "audio_base64": None, "input_lang": input_lang,
        })

    # ── Step 2: GPT (in French) ──────────────────────────────
    try:
        ai_text_fr = gpt_chat(session_id, user_text_fr)
        logger.info("GPT(fr): %s", ai_text_fr[:80])
    except Exception as e:
        logger.error("GPT failed: %s", e)
        raise HTTPException(500, f"AI failed: {e}")

    # ── Step 3: Translate French response → Bambara ──────────
    try:
        ai_text_bm = translate_to_bambara(ai_text_fr)
        logger.info("→ Bambara: %s", ai_text_bm[:80])
    except Exception as e:
        logger.warning("Translation failed: %s", e)
        ai_text_bm = ai_text_fr  # fallback to French

    # ── Step 4: TTS (Bambara) ────────────────────────────────
    audio_b64 = synthesize_to_b64(ai_text_bm)

    return JSONResponse({
        "user_text": user_text,
        "user_text_fr": user_text_fr,
        "ai_text_fr": ai_text_fr,
        "ai_text_bm": ai_text_bm,
        "audio_base64": audio_b64,
        "input_lang": input_lang,
        "session_id": session_id,
    })


# ── API: Text Chat ───────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    """Text chat: handles French or Bambara input."""
    try:
        if req.input_lang == "bm":
            user_text_fr = translate_bambara_to_french(req.text)
        else:
            user_text_fr = req.text

        ai_text_fr = gpt_chat(req.session_id, user_text_fr)
        ai_text_bm = translate_to_bambara(ai_text_fr)
        audio_b64 = synthesize_to_b64(ai_text_bm)

        return JSONResponse({
            "user_text_fr": user_text_fr,
            "ai_text_fr": ai_text_fr,
            "ai_text_bm": ai_text_bm,
            "audio_base64": audio_b64,
            "input_lang": req.input_lang,
        })
    except Exception as e:
        logger.error("Chat failed: %s", e)
        raise HTTPException(500, f"Chat failed: {e}")


# ── API: TTS ─────────────────────────────────────────────────
_audio_cache: dict[str, bytes] = {}
CACHE_SIZE = srv_cfg.get("cache_size", 128)


@app.post("/tts")
def tts_synthesize(req: TTSRequest):
    model = get_tts()
    key = hashlib.sha256(f"{req.speaker}::{req.text}".encode()).hexdigest()

    if key in _audio_cache:
        return Response(content=_audio_cache[key], media_type="audio/wav",
                        headers={"Content-Disposition": 'attachment; filename="ekodi.wav"'})

    try:
        wav = model.synthesize(req.text, speaker=req.speaker)
    except Exception as e:
        raise HTTPException(500, f"Synthesis failed: {e}")

    from src.audio_utils import audio_to_bytes
    wav_bytes = audio_to_bytes(wav, sr=model.sample_rate)

    if len(_audio_cache) >= CACHE_SIZE:
        del _audio_cache[next(iter(_audio_cache))]
    _audio_cache[key] = wav_bytes

    return Response(content=wav_bytes, media_type="audio/wav",
                    headers={"Content-Disposition": 'attachment; filename="ekodi.wav"'})


# ── Standalone ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)
