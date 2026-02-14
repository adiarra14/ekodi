"""
Ekodi – GPT chat service with token usage tracking.
"""

import logging
from dataclasses import dataclass
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

# ── Pricing per 1M tokens (USD) ──────────────────────────────
# Update these when OpenAI changes pricing
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "prompt": 2.50,        # $2.50 / 1M input tokens
        "completion": 10.00,   # $10.00 / 1M output tokens
    },
    "gpt-4o-mini": {
        "prompt": 0.15,
        "completion": 0.60,
    },
    "gpt-3.5-turbo": {
        "prompt": 0.50,
        "completion": 1.50,
    },
    "whisper-1": {
        "prompt": 0.006,  # per second of audio (special case)
        "completion": 0.0,
    },
}

DEFAULT_MODEL = "gpt-4o"


@dataclass
class ChatResult:
    """Result from a GPT call including token usage and cost."""
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> tuple[float, float, float]:
    """Calculate cost in USD for given token counts.
    Returns (prompt_cost, completion_cost, total_cost).
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])
    prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
    completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
    return prompt_cost, completion_cost, prompt_cost + completion_cost


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
    """Send French message to GPT-4o, get French response (legacy, no tracking)."""
    client = get_openai()
    add_to_conversation(session_id, "user", user_message_fr)
    messages = [{"role": "system", "content": GPT_SYSTEM}]
    messages.extend(get_conversation(session_id))

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        max_tokens=200,
        temperature=0.6,
    )
    ai_text = response.choices[0].message.content.strip()
    add_to_conversation(session_id, "assistant", ai_text)
    return ai_text


def gpt_chat_with_history(messages_history: list[dict], user_message_fr: str) -> ChatResult:
    """Chat with explicit message history (for DB-backed conversations).
    Returns ChatResult with text and full token usage/cost data.
    """
    client = get_openai()
    model = DEFAULT_MODEL
    messages = [{"role": "system", "content": GPT_SYSTEM}]
    messages.extend(messages_history[-MAX_HISTORY * 2:])
    messages.append({"role": "user", "content": user_message_fr})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=200,
        temperature=0.6,
    )

    ai_text = response.choices[0].message.content.strip()

    # Extract token usage
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    total_tokens = usage.total_tokens if usage else 0

    prompt_cost, completion_cost, total_cost = calculate_cost(model, prompt_tokens, completion_tokens)

    logger.info(
        "GPT usage: model=%s, prompt=%d, completion=%d, total=%d, cost=$%.6f",
        model, prompt_tokens, completion_tokens, total_tokens, total_cost,
    )

    return ChatResult(
        text=ai_text,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        prompt_cost=prompt_cost,
        completion_cost=completion_cost,
        total_cost=total_cost,
    )
