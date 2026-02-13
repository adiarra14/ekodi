"""
Ekodi – Chat routes (text chat, voice chat) with DB persistence.
"""

import logging
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.services.asr import transcribe_bambara, transcribe_french
from app.services.translation import translate_to_bambara, translate_bambara_to_french
from app.services.chat_ai import gpt_chat_with_history
from app.services.tts_service import synthesize_to_b64

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    input_lang: str = Field(default="fr")
    conversation_id: str | None = None


class ConversationCreate(BaseModel):
    title: str = Field(default="New Conversation", max_length=255)


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# ── Conversation CRUD ────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for current user."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    convos = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in convos
    ]


@router.post("/conversations")
async def create_conversation(
    req: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    convo = Conversation(user_id=user.id, title=req.title)
    db.add(convo)
    await db.flush()
    await db.refresh(convo)
    return {
        "id": convo.id,
        "title": convo.title,
        "created_at": convo.created_at.isoformat(),
        "updated_at": convo.updated_at.isoformat(),
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation with all messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found")

    # Eager-load messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == convo.id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return {
        "id": convo.id,
        "title": convo.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "text_fr": m.text_fr,
                "text_bm": m.text_bm,
                "audio_url": m.audio_url,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: str,
    req: ConversationRename,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found")
    convo.title = req.title
    await db.flush()
    return {"id": convo.id, "title": convo.title}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found")
    await db.delete(convo)
    return {"deleted": True}


# ── Helper: build GPT history from DB messages ───────────────

def _build_gpt_history(messages: list[Message]) -> list[dict]:
    """Convert DB messages to GPT message format."""
    history = []
    for m in messages:
        text = m.text_fr or m.text_bm or ""
        if text:
            history.append({"role": m.role, "content": text})
    return history


# ── Text Chat ────────────────────────────────────────────────

@router.post("/chat")
async def text_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Text chat with conversation persistence."""
    try:
        # Get or create conversation
        convo = None
        if req.conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == req.conversation_id,
                    Conversation.user_id == user.id,
                )
            )
            convo = result.scalar_one_or_none()

        if not convo:
            convo = Conversation(user_id=user.id, title=req.text[:50])
            db.add(convo)
            await db.flush()
            await db.refresh(convo)

        # Translate if Bambara input
        if req.input_lang == "bm":
            user_text_fr = translate_bambara_to_french(req.text)
            user_text_bm = req.text
        else:
            user_text_fr = req.text
            user_text_bm = None

        # Save user message
        user_msg = Message(
            conversation_id=convo.id,
            role="user",
            text_fr=user_text_fr,
            text_bm=user_text_bm,
        )
        db.add(user_msg)
        await db.flush()

        # Load history for GPT
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == convo.id)
            .order_by(Message.created_at)
        )
        all_msgs = result.scalars().all()
        gpt_history = _build_gpt_history(all_msgs[:-1])  # exclude current msg

        # GPT response (in French)
        ai_text_fr = gpt_chat_with_history(gpt_history, user_text_fr)
        ai_text_bm = translate_to_bambara(ai_text_fr)
        audio_b64 = synthesize_to_b64(ai_text_bm)

        # Save AI message
        ai_msg = Message(
            conversation_id=convo.id,
            role="assistant",
            text_fr=ai_text_fr,
            text_bm=ai_text_bm,
        )
        db.add(ai_msg)
        await db.flush()
        await db.refresh(ai_msg)

        return JSONResponse({
            "conversation_id": convo.id,
            "message_id": ai_msg.id,
            "user_text_fr": user_text_fr,
            "ai_text_fr": ai_text_fr,
            "ai_text_bm": ai_text_bm,
            "audio_base64": audio_b64,
            "input_lang": req.input_lang,
        })
    except Exception as e:
        logger.error("Chat failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Chat failed: {e}")


# ── Voice Chat ───────────────────────────────────────────────

@router.post("/voice-chat")
async def voice_chat(
    audio: UploadFile = File(...),
    input_lang: str = Form(default="fr"),
    conversation_id: str = Form(default=""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Voice pipeline: audio → ASR → GPT → translate → TTS."""
    suffix = "." + (audio.filename.split(".")[-1] if audio.filename else "webm")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # ASR
        if input_lang == "bm":
            user_text = transcribe_bambara(tmp_path)
            user_text_fr = translate_bambara_to_french(user_text) if user_text else ""
        else:
            user_text = transcribe_french(tmp_path)
            user_text_fr = user_text
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

    # Get or create conversation
    convo = None
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        convo = result.scalar_one_or_none()

    if not convo:
        convo = Conversation(user_id=user.id, title=user_text[:50])
        db.add(convo)
        await db.flush()
        await db.refresh(convo)

    # Save user message
    user_msg = Message(
        conversation_id=convo.id,
        role="user",
        text_fr=user_text_fr,
        text_bm=user_text if input_lang == "bm" else None,
    )
    db.add(user_msg)
    await db.flush()

    # GPT
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == convo.id)
        .order_by(Message.created_at)
    )
    all_msgs = result.scalars().all()
    gpt_history = _build_gpt_history(all_msgs[:-1])
    ai_text_fr = gpt_chat_with_history(gpt_history, user_text_fr)

    # Translate + TTS
    ai_text_bm = translate_to_bambara(ai_text_fr)
    audio_b64 = synthesize_to_b64(ai_text_bm)

    # Save AI message
    ai_msg = Message(
        conversation_id=convo.id,
        role="assistant",
        text_fr=ai_text_fr,
        text_bm=ai_text_bm,
    )
    db.add(ai_msg)
    await db.flush()
    await db.refresh(ai_msg)

    return JSONResponse({
        "conversation_id": convo.id,
        "message_id": ai_msg.id,
        "user_text": user_text,
        "user_text_fr": user_text_fr,
        "ai_text_fr": ai_text_fr,
        "ai_text_bm": ai_text_bm,
        "audio_base64": audio_b64,
        "input_lang": input_lang,
    })
