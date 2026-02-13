"""
Ekodi – Public API v1 (API-key authenticated).
"""

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_api_key_user, get_current_user, generate_api_key
from app.models.user import User
from app.models.api_key import ApiKey
from app.services.tts_service import synthesize_to_wav, synthesize_to_b64
from app.services.translation import translate_to_bambara, translate_bambara_to_french
from app.services.chat_ai import gpt_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api"])


# ── Request models ────────────────────────────────────────────

class TTSApiRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class TranslateApiRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source: str = Field(default="fr", description="'fr' or 'bm'")
    target: str = Field(default="bm", description="'fr' or 'bm'")


class ChatApiRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default")


# ── API Key management (JWT-authenticated) ────────────────────

class CreateKeyRequest(BaseModel):
    name: str = Field(default="Default", max_length=100)


@router.get("/keys")
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's API keys."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "usage_count": k.usage_count,
            "rate_limit": k.rate_limit,
            "active": k.active,
            "created_at": k.created_at.isoformat(),
        }
        for k in keys
    ]


@router.post("/keys")
async def create_key(
    req: CreateKeyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key."""
    raw_key, key_hash = generate_api_key()
    ak = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=raw_key[:12] + "...",
        name=req.name,
    )
    db.add(ak)
    await db.flush()
    return {"key": raw_key, "id": ak.id, "name": ak.name}


@router.delete("/keys/{key_id}")
async def revoke_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    ak = result.scalar_one_or_none()
    if not ak:
        raise HTTPException(404, "Key not found")
    ak.active = False
    return {"revoked": True}


# ── Public API endpoints (API-key authenticated) ─────────────

@router.post("/tts")
async def api_tts(
    req: TTSApiRequest,
    user: User = Depends(get_api_key_user),
):
    """Synthesize Bambara text → WAV audio."""
    try:
        wav_bytes = synthesize_to_wav(req.text)
    except Exception as e:
        raise HTTPException(500, f"TTS failed: {e}")
    return Response(content=wav_bytes, media_type="audio/wav")


@router.post("/translate")
async def api_translate(
    req: TranslateApiRequest,
    user: User = Depends(get_api_key_user),
):
    """Translate between French and Bambara."""
    try:
        if req.source == "fr" and req.target == "bm":
            result = translate_to_bambara(req.text)
        elif req.source == "bm" and req.target == "fr":
            result = translate_bambara_to_french(req.text)
        else:
            raise HTTPException(400, "Supported: fr→bm or bm→fr")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Translation failed: {e}")

    return {"source": req.source, "target": req.target, "text": req.text, "translation": result}


@router.post("/chat")
async def api_chat(
    req: ChatApiRequest,
    user: User = Depends(get_api_key_user),
):
    """Chat with Ekodi AI (French in/out)."""
    try:
        session_key = f"api-{user.id}-{req.session_id}"
        ai_response = gpt_chat(session_key, req.message)
        ai_bm = translate_to_bambara(ai_response)
        audio_b64 = synthesize_to_b64(ai_bm)
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {e}")

    return {
        "response_fr": ai_response,
        "response_bm": ai_bm,
        "audio_base64": audio_b64,
    }
