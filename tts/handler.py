"""
Custom handler for Hugging Face Inference Endpoints.

Uses Meta MMS-TTS (VITS architecture) for Bambara text-to-speech.

This file is uploaded alongside the model weights to HF Hub.
When deployed via Inference Endpoints, HF will use this handler
to process incoming requests.

Expected request format:
    POST /
    {
        "inputs": "I ni ce, aw ka kɛnɛ wa?",
        "parameters": {}
    }

Returns: WAV audio bytes with Content-Type: audio/wav
"""

import io
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch

logger = logging.getLogger(__name__)


class EndpointHandler:
    """HF Inference Endpoints custom handler for Ekodi Bambara TTS (MMS-VITS)."""

    def __init__(self, model_dir: str, **kwargs):
        """Load VITS model and tokenizer."""
        from transformers import VitsModel, AutoTokenizer

        model_path = Path(model_dir)
        logger.info("Loading Ekodi Bambara TTS (MMS-VITS) from %s ...", model_path)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        self.model = VitsModel.from_pretrained(str(model_path)).to(self.device)
        self.model.eval()

        self.sample_rate = 16_000
        logger.info("Model loaded on %s. Ready.", self.device)

    def _normalize_text(self, text: str) -> str:
        """Basic Bambara text normalisation (inline, no external deps)."""
        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"[\u2018\u2019\u0060\u00B4\u2032]", "'", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = text.lower()
        return text

    @torch.inference_mode()
    def __call__(self, data: dict[str, Any]) -> Any:
        """
        Process an inference request.

        Args:
            data: {"inputs": "Bambara text here", "parameters": {...}}

        Returns:
            WAV audio bytes
        """
        text = data.get("inputs", "")
        if not text:
            return {"error": "No input text provided"}

        text = self._normalize_text(text)
        logger.info("Synthesizing: %s", text[:100])

        # Tokenize and generate
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        output = self.model(**inputs)
        waveform = output.waveform[0].cpu().numpy()

        # Convert to WAV bytes
        buf = io.BytesIO()
        sf.write(buf, waveform, self.sample_rate, format="WAV", subtype="PCM_16")
        buf.seek(0)

        return buf.read()
