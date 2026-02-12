#!/usr/bin/env python3
"""Quick test of the pre-trained MMS-TTS Bambara model."""
import torch
from transformers import VitsModel, AutoTokenizer
import soundfile as sf
from pathlib import Path

print("Loading facebook/mms-tts-bam...")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-bam")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = VitsModel.from_pretrained("facebook/mms-tts-bam").to(device)
model.eval()

out_dir = Path("data/test_outputs")
out_dir.mkdir(parents=True, exist_ok=True)

tests = [
    "I ni ce",
    "Aw ni ce, ne togo ye Ekodi",
    "Bamanankan ye kan nafama ye",
]

for i, text in enumerate(tests):
    tokens = tokenizer(text, return_tensors="pt").to(device)
    with torch.no_grad():
        output = model(**tokens)
    wav = output.waveform[0].cpu().numpy()
    path = out_dir / f"test_{i}.wav"
    sf.write(str(path), wav, model.config.sampling_rate)
    dur = len(wav) / model.config.sampling_rate
    print(f'  [{i}] "{text}" -> {path} ({dur:.1f}s, sr={model.config.sampling_rate})')

print("Done! Pre-trained model works for Bambara.")
