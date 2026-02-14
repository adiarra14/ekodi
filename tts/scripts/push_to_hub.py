#!/usr/bin/env python3
"""
Push the fine-tuned Ekodi Bambara TTS model to Hugging Face Hub.

Uploads:
  - Model weights (MMS-TTS / VITS checkpoint)
  - Tokenizer
  - Custom inference handler (handler.py)
  - Config file
  - Model card (README.md)

Usage:
    python scripts/push_to_hub.py --repo-id your-username/ekodi-bambara-tts
    python scripts/push_to_hub.py --repo-id your-username/ekodi-bambara-tts --private
"""

import argparse
import logging
import shutil
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


MODEL_CARD_TEMPLATE = """\
---
language:
- bm
license: cc-by-nc-4.0
tags:
- text-to-speech
- tts
- bambara
- bamanankan
- ekodi
- mms
- vits
pipeline_tag: text-to-speech
library_name: transformers
---

# Ekodi Bambara TTS

A **Meta MMS-TTS (VITS)** model fine-tuned for **Bambara (Bamanankan)**.

Based on `facebook/mms-tts-bam` — end-to-end VITS architecture (no separate vocoder needed).

## Usage

```python
import soundfile as sf
from transformers import VitsModel, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("{repo_id}")
model = VitsModel.from_pretrained("{repo_id}")

inputs = tokenizer("I ni ce, i ka kɛnɛ wa?", return_tensors="pt")
with torch.no_grad():
    output = model(**inputs)

sf.write("output.wav", output.waveform[0].numpy(), 16000)
```

## Details

- **Language**: Bambara / Bamanankan (bm)
- **Base model**: facebook/mms-tts-bam (Meta MMS)
- **Architecture**: VITS (end-to-end, built-in vocoder)
- **Sample rate**: 16 kHz
- **Training data**: Open Bambara speech datasets
"""


def main():
    parser = argparse.ArgumentParser(description="Push model to Hugging Face Hub")
    parser.add_argument("--repo-id", required=True, help="HF Hub repo id, e.g. your-username/ekodi-bambara-tts")
    parser.add_argument("--checkpoint", default=None, help="Path to checkpoint dir (default: from config)")
    parser.add_argument("--config", default="config/tts-port.yml")
    parser.add_argument("--private", action="store_true", help="Make the repo private")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    checkpoint_dir = Path(args.checkpoint or (cfg["training"]["output_dir"] + "/best"))

    if not checkpoint_dir.exists():
        logger.error("Checkpoint not found at %s. Run train.py first.", checkpoint_dir)
        return

    from huggingface_hub import HfApi, create_repo

    api = HfApi()

    # Create repo
    logger.info("Creating repo %s (private=%s) ...", args.repo_id, args.private)
    create_repo(args.repo_id, repo_type="model", private=args.private, exist_ok=True)

    # Upload model files
    logger.info("Uploading model checkpoint from %s ...", checkpoint_dir)
    api.upload_folder(
        folder_path=str(checkpoint_dir),
        repo_id=args.repo_id,
        repo_type="model",
    )

    # Upload handler.py for Inference Endpoints
    handler_path = Path(__file__).parent.parent / "handler.py"
    if handler_path.exists():
        logger.info("Uploading handler.py ...")
        api.upload_file(
            path_or_fileobj=str(handler_path),
            path_in_repo="handler.py",
            repo_id=args.repo_id,
            repo_type="model",
        )

    # Upload config
    config_path = Path(args.config)
    if config_path.exists():
        api.upload_file(
            path_or_fileobj=str(config_path),
            path_in_repo="config.yaml",
            repo_id=args.repo_id,
            repo_type="model",
        )

    # Generate and upload model card
    model_card = MODEL_CARD_TEMPLATE.format(repo_id=args.repo_id)
    card_path = checkpoint_dir / "README.md"
    card_path.write_text(model_card, encoding="utf-8")
    api.upload_file(
        path_or_fileobj=str(card_path),
        path_in_repo="README.md",
        repo_id=args.repo_id,
        repo_type="model",
    )

    logger.info("Done! Model pushed to: https://huggingface.co/%s", args.repo_id)
    logger.info("")
    logger.info("To deploy via Inference Endpoints:")
    logger.info("  1. Go to https://huggingface.co/%s", args.repo_id)
    logger.info("  2. Click 'Deploy' → 'Inference Endpoints'")
    logger.info("  3. Select GPU (T4 recommended), deploy")
    logger.info("  4. Your API will be at: https://xxxx.endpoints.huggingface.cloud")


if __name__ == "__main__":
    main()
