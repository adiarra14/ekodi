"""
Ekodi – Translation service (Meta NLLB: French ↔ Bambara).
"""

import logging

logger = logging.getLogger(__name__)

_nllb_model = None
_nllb_tokenizer = None


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


def translate_to_bambara(french_text: str) -> str:
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


def translate_bambara_to_french(bambara_text: str) -> str:
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
