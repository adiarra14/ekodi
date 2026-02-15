"""
Ekodi – Translation service (French ↔ Bambara).
Supports two engines: NLLB (local Meta model) and GPT (OpenAI API).
The active engine is determined by: DB platform_settings > env var > default.
"""

import logging
import os

logger = logging.getLogger(__name__)

# ── In-memory cache of the active engine (refreshed from DB on each call) ──
_engine_cache: str | None = None
_engine_cache_ts: float = 0
_ENGINE_CACHE_TTL = 30  # seconds

# ── NLLB state ──
_nllb_model = None
_nllb_tokenizer = None


# ═══════════════════════════════════════════════════════════════
# Engine selection
# ═══════════════════════════════════════════════════════════════

def get_translation_engine() -> str:
    """Return the active translation engine: 'gpt' or 'nllb'.
    Priority: DB platform_settings > EKODI_TRANSLATION_ENGINE env > 'gpt'.
    Uses an in-memory cache with a 30s TTL to avoid DB lookups on every call.
    """
    import time
    global _engine_cache, _engine_cache_ts

    now = time.time()
    if _engine_cache and (now - _engine_cache_ts) < _ENGINE_CACHE_TTL:
        return _engine_cache

    # Try DB lookup (non-blocking, with fallback)
    engine = _read_engine_from_db()
    if not engine:
        engine = os.getenv("EKODI_TRANSLATION_ENGINE", "nllb").lower()

    if engine not in ("gpt", "nllb"):
        engine = "gpt"

    _engine_cache = engine
    _engine_cache_ts = now
    return engine


def _read_engine_from_db() -> str | None:
    """Synchronous read from platform_settings (best-effort)."""
    try:
        from sqlalchemy import create_engine, text
        from app.config import get_settings
        settings = get_settings()
        # Build sync URL from async URL
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
        eng = create_engine(sync_url)
        with eng.connect() as conn:
            row = conn.execute(
                text("SELECT value FROM platform_settings WHERE key = :k"),
                {"k": "translation_engine"},
            ).fetchone()
            if row:
                return row[0]
    except Exception:
        pass  # table may not exist yet, or other DB issue
    return None


def invalidate_engine_cache():
    """Call after an admin changes the setting to force an immediate re-read."""
    global _engine_cache, _engine_cache_ts
    _engine_cache = None
    _engine_cache_ts = 0


# ═══════════════════════════════════════════════════════════════
# NLLB engine (local Meta NLLB model)
# ═══════════════════════════════════════════════════════════════

def get_nllb():
    """Load Meta NLLB translation model (lazy loaded)."""
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


def nllb_translate_to_bambara(french_text: str) -> str:
    """Translate French → Bambara using Meta NLLB."""
    import torch

    model, tokenizer = get_nllb()
    tokenizer.src_lang = "fra_Latn"
    inputs = tokenizer(french_text, return_tensors="pt", max_length=256, truncation=True)
    with torch.no_grad():
        tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids("bam_Latn"),
            max_new_tokens=256,
        )
    return tokenizer.decode(tokens[0], skip_special_tokens=True)


def nllb_translate_bambara_to_french(bambara_text: str) -> str:
    """Translate Bambara → French using Meta NLLB."""
    import torch

    model, tokenizer = get_nllb()
    tokenizer.src_lang = "bam_Latn"
    inputs = tokenizer(bambara_text, return_tensors="pt", max_length=256, truncation=True)
    with torch.no_grad():
        tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids("fra_Latn"),
            max_new_tokens=256,
        )
    return tokenizer.decode(tokens[0], skip_special_tokens=True)


# ═══════════════════════════════════════════════════════════════
# GPT engine (OpenAI GPT-4o-mini)
# ═══════════════════════════════════════════════════════════════

TRANSLATE_MODEL = "gpt-4o-mini"

_BM_TO_FR_PROMPT = (
    "Tu es un traducteur expert bambara (bamanankan) → français. "
    "Traduis le texte bambara suivant en français naturel et clair. "
    "Ne réponds qu'avec la traduction, rien d'autre."
)

_FR_TO_BM_PROMPT = (
    "Tu es un traducteur expert français → bambara (bamanankan). "
    "Traduis le texte français suivant en bambara naturel et correct. "
    "Utilise l'orthographe standard du bambara. "
    "Ne réponds qu'avec la traduction, rien d'autre."
)


def gpt_translate_bm_to_fr(bambara_text: str) -> str:
    """Translate Bambara → French using GPT-4o-mini."""
    from app.services.chat_ai import get_openai
    client = get_openai()
    resp = client.chat.completions.create(
        model=TRANSLATE_MODEL,
        messages=[
            {"role": "system", "content": _BM_TO_FR_PROMPT},
            {"role": "user", "content": bambara_text},
        ],
        max_tokens=300,
        temperature=0.3,
    )
    result = resp.choices[0].message.content.strip()
    logger.info("GPT bm→fr: '%s' → '%s'", bambara_text[:60], result[:60])
    return result


def gpt_translate_fr_to_bm(french_text: str) -> str:
    """Translate French → Bambara using GPT-4o-mini."""
    from app.services.chat_ai import get_openai
    client = get_openai()
    resp = client.chat.completions.create(
        model=TRANSLATE_MODEL,
        messages=[
            {"role": "system", "content": _FR_TO_BM_PROMPT},
            {"role": "user", "content": french_text},
        ],
        max_tokens=300,
        temperature=0.3,
    )
    result = resp.choices[0].message.content.strip()
    logger.info("GPT fr→bm: '%s' → '%s'", french_text[:60], result[:60])
    return result


# ═══════════════════════════════════════════════════════════════
# Public API (used by chat.py) — dispatches to active engine
# with cross-engine fallback
# ═══════════════════════════════════════════════════════════════

def translate_bambara_to_french(bambara_text: str) -> str:
    """Translate Bambara → French using the active engine, with fallback."""
    engine = get_translation_engine()
    logger.info("Translating bm→fr with engine=%s", engine)

    if engine == "gpt":
        try:
            return gpt_translate_bm_to_fr(bambara_text)
        except Exception as e:
            logger.warning("GPT bm→fr failed (%s), falling back to NLLB", e)
            try:
                return nllb_translate_bambara_to_french(bambara_text)
            except Exception as e2:
                logger.error("NLLB fallback bm→fr also failed: %s", e2)
                return bambara_text  # return raw text as last resort
    else:
        try:
            return nllb_translate_bambara_to_french(bambara_text)
        except Exception as e:
            logger.warning("NLLB bm→fr failed (%s), falling back to GPT", e)
            try:
                return gpt_translate_bm_to_fr(bambara_text)
            except Exception as e2:
                logger.error("GPT fallback bm→fr also failed: %s", e2)
                return bambara_text


def translate_to_bambara(french_text: str) -> str:
    """Translate French → Bambara using the active engine, with fallback."""
    engine = get_translation_engine()
    logger.info("Translating fr→bm with engine=%s", engine)

    if engine == "gpt":
        try:
            return gpt_translate_fr_to_bm(french_text)
        except Exception as e:
            logger.warning("GPT fr→bm failed (%s), falling back to NLLB", e)
            try:
                return nllb_translate_to_bambara(french_text)
            except Exception as e2:
                logger.error("NLLB fallback fr→bm also failed: %s", e2)
                return french_text
    else:
        try:
            return nllb_translate_to_bambara(french_text)
        except Exception as e:
            logger.warning("NLLB fr→bm failed (%s), falling back to GPT", e)
            try:
                return gpt_translate_fr_to_bm(french_text)
            except Exception as e2:
                logger.error("GPT fallback fr→bm also failed: %s", e2)
                return french_text
