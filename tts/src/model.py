"""
Ekodi Bambara TTS – Model wrapper.

Uses Meta MMS-TTS (VITS architecture) as foundation.
  - Model: facebook/mms-tts-bam  (pretrained Bambara)
  - Architecture: VITS (end-to-end, built-in vocoder, no speaker embeddings)
  - Output: 16 kHz mono WAV

Usage:
    model = EkodiTTS.from_config("config/ekodi-port.yml")
    wav   = model.synthesize("I ni ce!")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import yaml

logger = logging.getLogger(__name__)


class EkodiTTS:
    """Unified TTS inference wrapper for Meta MMS-TTS (VITS)."""

    def __init__(
        self,
        model_name: str = "facebook/mms-tts-bam",
        checkpoint: Optional[str] = None,
        device: str = "auto",
        cache_size: int = 128,
    ):
        self.backend = "mms-vits"
        self.device = self._resolve_device(device)
        self._cache_size = cache_size
        self._init_mms(model_name, checkpoint)
        logger.info("EkodiTTS ready  backend=%s  device=%s  model=%s",
                     self.backend, self.device, checkpoint or model_name)

    # ── Constructors ──────────────────────────────────────────
    @classmethod
    def from_config(cls, config_path: str | Path) -> "EkodiTTS":
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        model_cfg = cfg.get("model", {})
        inf_cfg = cfg.get("inference", {})
        srv_cfg = cfg.get("server", {})
        return cls(
            model_name=model_cfg.get("base_model", "facebook/mms-tts-bam"),
            checkpoint=inf_cfg.get("checkpoint"),
            device=inf_cfg.get("device", "auto"),
            cache_size=srv_cfg.get("cache_size", 128),
        )

    # ── MMS-TTS / VITS init ──────────────────────────────────
    def _init_mms(self, model_name: str, checkpoint: Optional[str]):
        from transformers import VitsModel, AutoTokenizer

        model_id = checkpoint or model_name
        logger.info("Loading MMS-TTS (VITS) from %s ...", model_id)

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = VitsModel.from_pretrained(model_id).to(self.device)
        self.model.eval()

        # VITS is end-to-end: no separate vocoder or speaker embeddings needed
        logger.info("Model loaded. Parameters: %.1fM",
                     sum(p.numel() for p in self.model.parameters()) / 1e6)

    # ── Synthesis ─────────────────────────────────────────────
    def synthesize(
        self,
        text: str,
        speaker: str = "ekodi",
    ) -> np.ndarray:
        """
        Convert Bambara text to a 16 kHz float32 numpy waveform.
        """
        from .text_normalize import normalize_bambara
        text = normalize_bambara(text)
        return self._synthesize_vits(text)

    @torch.inference_mode()
    def _synthesize_vits(self, text: str) -> np.ndarray:
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        output = self.model(**inputs)
        waveform = output.waveform[0].cpu().numpy()
        return waveform

    # ── Helpers ───────────────────────────────────────────────
    @staticmethod
    def _resolve_device(device: str) -> torch.device:
        if device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(device)

    @property
    def sample_rate(self) -> int:
        """MMS-TTS outputs 16 kHz audio."""
        return 16_000
