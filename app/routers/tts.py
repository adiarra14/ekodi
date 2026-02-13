"""
Ekodi – TTS route.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.tts_service import synthesize_to_wav

router = APIRouter(tags=["tts"])


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    speaker: str = Field(default="ekodi")


@router.post("/tts")
def tts_synthesize(req: TTSRequest, user: User = Depends(get_current_user)):
    """Synthesize Bambara text → WAV audio."""
    try:
        wav_bytes = synthesize_to_wav(req.text, speaker=req.speaker)
    except Exception as e:
        raise HTTPException(500, f"Synthesis failed: {e}")

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": 'attachment; filename="ekodi.wav"'},
    )
