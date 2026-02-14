# Ekodi Bambara TTS

Text-to-Speech for **Bambara (Bamanankan)** — based on **Meta MMS-TTS (VITS)**,
fine-tuned and deployable via Hugging Face Inference Endpoints.

**Foundation**: `facebook/mms-tts-bam` — Meta's Massively Multilingual Speech
project, VITS architecture (end-to-end, no separate vocoder needed).

---

## Quick start (5 minutes)

```bash
cd tts
pip install -r requirements.txt

# 1. Download open Bambara data
python scripts/download_data.py

# 2. Preprocess (normalise text + audio)
python scripts/prepare_data.py

# 3. Fine-tune MMS-TTS on Bambara
python scripts/train.py

# 4. Run the local API server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# 5. Test it
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "I ni ce!"}' --output test.wav
```

---

## Project structure

```
tts/
├── config/
│   └── tts-port.yml           # all settings (model, data, training, server)
├── scripts/
│   ├── download_data.py        # download open Bambara datasets
│   ├── prepare_data.py         # normalise audio + text, split
│   ├── train.py                # fine-tune MMS-TTS (VITS) on Bambara
│   └── push_to_hub.py         # push model to HuggingFace Hub
├── server/
│   └── app.py                  # FastAPI inference server
├── handler.py                  # HF Inference Endpoints custom handler
├── src/
│   ├── model.py                # model wrapper (MMS-TTS / VITS)
│   ├── text_normalize.py       # Bambara text normalisation
│   └── audio_utils.py          # audio processing utilities
├── eval/
│   └── test_prompts.txt        # Bambara test sentences
├── requirements.txt
└── README.md
```

---

## Step-by-step guide

### 1. Download data

```bash
python scripts/download_data.py
```

Tries multiple open sources (MALIBA-AI, oza75, Common Voice) and saves
audio + text pairs to `data/raw/`.

**Bring your own data?** Place WAV files in `data/raw/` and create a CSV file
`data/raw/raw_metadata.csv` with columns: `file_path`, `text`, `speaker_id`.

### 2. Prepare data

```bash
python scripts/prepare_data.py
```

- Resamples all audio to 16 kHz mono
- Peak-normalises and trims silence
- Normalises Bambara text (numbers to words, diacritics, apostrophes)
- Splits into train / validation

Output: `data/processed/metadata.csv` + `data/processed/wavs/`

### 3. Train

```bash
python scripts/train.py
```

Fine-tunes `facebook/mms-tts-bam` (VITS) on your Bambara data.
Designed for 8-12 GB VRAM (fp16, gradient accumulation).

Settings in `config/tts-port.yml` → `training:` section.

To resume from a checkpoint:
```bash
python scripts/train.py --resume-from checkpoints/checkpoint-500
```

### 4. Run local server

```bash
cd tts
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

API endpoints:
- `POST /tts` — `{"text": "...", "speaker": "ekodi"}` → WAV audio
- `GET /health` — health check
- `GET /speakers` — list speakers

### 5. Deploy to Hugging Face

```bash
# Login first
huggingface-cli login

# Push model + handler to HF Hub
python scripts/push_to_hub.py --repo-id your-username/ekodi-bambara-tts

# Then go to https://huggingface.co/your-username/ekodi-bambara-tts
# Click "Deploy" → "Inference Endpoints" → select T4 GPU → Deploy
```

Your API will be live at `https://xxxx.endpoints.huggingface.cloud`.

Call it:
```python
import requests

API_URL = "https://xxxx.endpoints.huggingface.cloud"
headers = {"Authorization": "Bearer hf_..."}

response = requests.post(API_URL, json={
    "inputs": "I ni ce, aw ka kɛnɛ wa?"
}, headers=headers)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

---

## Why Meta MMS-TTS?

| Feature | MMS-TTS (VITS) |
|---------|----------------|
| **Bambara support** | Pretrained checkpoint exists (`facebook/mms-tts-bam`) |
| **Architecture** | VITS — end-to-end (no separate vocoder) |
| **Simplicity** | No speaker embeddings needed |
| **Input** | Grapheme-based (no phonemizer required for Bambara) |
| **Languages** | 1100+ languages covered by MMS |
| **License** | CC-BY-NC 4.0 |

---

## Configuration

All settings are in `config/tts-port.yml`. Key sections:

| Section | What it controls |
|---------|-----------------|
| `model` | Base model (`facebook/mms-tts-bam`), architecture |
| `data` | Paths, sample rate, duration limits, dataset sources |
| `training` | Epochs, batch size, LR, VRAM optimisations |
| `inference` | Checkpoint path, device, max length |
| `server` | Host, port, CORS, cache size |
| `hub` | HuggingFace Hub repo settings |

---

## Hardware requirements

| Task | Minimum | Recommended |
|------|---------|-------------|
| Training | 8 GB VRAM GPU | 12+ GB VRAM GPU |
| Inference (GPU) | 2 GB VRAM | 4 GB VRAM |
| Inference (CPU) | 4 GB RAM | 8 GB RAM |

Cloud training: Use Google Colab (free T4), RunPod, or Lambda Cloud.

---

## Retraining with more data

1. Add more WAV + transcript pairs to `data/raw/raw_metadata.csv`
2. Re-run `python scripts/prepare_data.py`
3. Re-run `python scripts/train.py --resume-from checkpoints/best`
4. Re-push: `python scripts/push_to_hub.py --repo-id your-username/ekodi-bambara-tts`
