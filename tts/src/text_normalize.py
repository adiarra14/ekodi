"""
Bambara (Bamanankan) text normalisation for TTS.

Handles:
  - Unicode NFC normalisation
  - Consistent apostrophe / diacritics
  - Number → written-word conversion  (Arabic numerals break most TTS models)
  - Punctuation clean-up
  - Whitespace normalisation
"""

import re
import unicodedata


# ── Number words (Bambara) ────────────────────────────────────
_ONES = {
    0: "furaw",
    1: "kelen",
    2: "fila",
    3: "saba",
    4: "naani",
    5: "duuru",
    6: "wɔɔrɔ",
    7: "wolonwula",
    8: "seegi",
    9: "kɔnɔntɔn",
}

_TENS = {
    10: "tan",
    20: "mugan",
    30: "bi saba",
    40: "bi naani",
    50: "bi duuru",
    60: "bi wɔɔrɔ",
    70: "bi wolonwula",
    80: "bi seegi",
    90: "bi kɔnɔntɔn",
}

_BIG = {
    100: "kɛmɛ",
    1000: "waa",
}


def _number_to_bambara(n: int) -> str:
    """Convert an integer (0-9999) to Bambara words.  Best-effort."""
    if n < 0:
        return "kɛlɛn kɔnɔ " + _number_to_bambara(-n)
    if n in _ONES:
        return _ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        base = _TENS.get(tens * 10, f"bi {_ONES.get(tens, str(tens))}")
        if ones == 0:
            return base
        return f"{base} ni {_ONES.get(ones, str(ones))}"
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        prefix = f"{_BIG[100]} {_ONES.get(hundreds, str(hundreds))}" if hundreds > 1 else _BIG[100]
        if rest == 0:
            return prefix
        return f"{prefix} ni {_number_to_bambara(rest)}"
    if n < 10000:
        thousands, rest = divmod(n, 1000)
        prefix = f"{_BIG[1000]} {_ONES.get(thousands, str(thousands))}" if thousands > 1 else _BIG[1000]
        if rest == 0:
            return prefix
        return f"{prefix} ni {_number_to_bambara(rest)}"
    return str(n)  # fallback for very large numbers


def _replace_numbers(text: str) -> str:
    """Replace sequences of digits with Bambara number words."""
    def _sub(m: re.Match) -> str:
        try:
            return _number_to_bambara(int(m.group()))
        except (ValueError, KeyError):
            return m.group()
    return re.sub(r"\d+", _sub, text)


# ── Apostrophe / quote normalisation ─────────────────────────
_APOSTROPHE_RE = re.compile(r"[\u2018\u2019\u0060\u00B4\u2032]")  # curly / backtick / acute / prime


# ── Main entry point ─────────────────────────────────────────
def normalize_bambara(text: str) -> str:
    """Full normalisation pipeline for a single Bambara sentence."""
    # 1. Unicode NFC
    text = unicodedata.normalize("NFC", text)

    # 2. Consistent apostrophes → ASCII straight quote
    text = _APOSTROPHE_RE.sub("'", text)

    # 3. Numbers → words
    text = _replace_numbers(text)

    # 4. Remove non-Bambara special characters (keep letters, digits, basic punct)
    #    Bambara uses: a-z, ɛ, ɔ, ɲ, ŋ, plus tone marks (à, á, è, é, etc.)
    text = re.sub(r"[^\w\s\.\,\;\:\!\?\-\']", " ", text)

    # 5. Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # 6. Lowercase (Bambara TTS models typically expect lowercase)
    text = text.lower()

    return text


# ── Convenience for batch use ─────────────────────────────────
def normalize_batch(texts: list[str]) -> list[str]:
    return [normalize_bambara(t) for t in texts]


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    samples = [
        "I ni ce! Aw ni tile.",
        "A bɛ 350 CFA sara.",
        "N'tara 2024 san kɔnɔ.",
        "Bamanankan ye kan ɲuman ye!",
    ]
    for s in samples:
        print(f"  IN:  {s}")
        print(f"  OUT: {normalize_bambara(s)}")
        print()
