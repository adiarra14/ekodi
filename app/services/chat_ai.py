"""
Ekodi – GPT chat service.
"""

import logging
from openai import OpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)

_openai_client = None

GPT_SYSTEM = """Tu es Ekodi, un assistant vocal IA amical pour les locuteurs bambara au Mali.

Règles:
- Réponds TOUJOURS en français clair et simple
- Sois chaleureux et respectueux, comme un ami malien
- Réponses COURTES (1-3 phrases) — c'est une conversation vocale
- Si l'utilisateur te salue, salue-le chaleureusement
- Tu aides avec: questions générales, culture malienne/bambara, traductions, conversation quotidienne
- Si le message est en bambara, comprends l'intention et réponds en français"""

# In-memory conversation store (will be replaced by DB in authenticated mode)
_conversations: dict[str, list] = {}
MAX_HISTORY = 10


def get_openai():
    """Lazy-load OpenAI client."""
    global _openai_client
    if _openai_client is None:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("OpenAI client ready")
    return _openai_client


def get_conversation(session_id: str) -> list:
    if session_id not in _conversations:
        _conversations[session_id] = []
    return _conversations[session_id]


def add_to_conversation(session_id: str, role: str, content: str):
    conv = get_conversation(session_id)
    conv.append({"role": role, "content": content})
    if len(conv) > MAX_HISTORY * 2:
        _conversations[session_id] = conv[-(MAX_HISTORY * 2):]


def gpt_chat(session_id: str, user_message_fr: str) -> str:
    """Send French message to GPT-4o, get French response."""
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


def gpt_chat_with_history(messages_history: list[dict], user_message_fr: str) -> str:
    """Chat with explicit message history (for DB-backed conversations)."""
    client = get_openai()
    messages = [{"role": "system", "content": GPT_SYSTEM}]
    messages.extend(messages_history[-MAX_HISTORY * 2:])
    messages.append({"role": "user", "content": user_message_fr})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=200,
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()
