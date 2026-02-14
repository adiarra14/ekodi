#!/usr/bin/env python3
"""
Generate demo voice for the landing page.
Sentence-by-sentence generation for natural flow.
"""
import torch
import numpy as np
import soundfile as sf
from transformers import VitsModel, AutoTokenizer
from pathlib import Path

# Each sentence generated separately for better quality
# Pause duration (seconds) after each sentence
SENTENCES = [
    ("Mali ye jamana belebeleba ye, Afriki Tlebi fe.", 0.6),
    ("Mogo miliyon mugan ni saba, be a kono.", 0.5),
    ("Bamako de ye a faaba ye, dugu min sigilen be Ba Joliba da la.", 0.6),
    ("Tumbutu, ani Jene, olu fana ye dugu koroba u ye.", 0.5),
    ("Jamana bonya ye kilometre miliyon kelen ni fila ye.", 0.5),
    ("Kogoji be a Keneka fe.", 0.4),
    ("Bamanankan ye kanba ye.", 0.5),
    ("Mogo keme o keme sarada bi-segin ba fo.", 0.5),
    ("Nka, kan werew be yen, i na fo, Fula kan, Senufo kan, Marakan kan, ani Dogon.", 0.6),
    ("Mali ye a ka yeremaoronya soro, san ba kelen, keme konondon, ni bi-wooro, Setanburu kalo la.", 0.6),
    ("Mali ye Jatigiya jamana ye.", 0.5),
    ("Sinankunya be here sabati mogow ce.", 0.5),
    ("Sanu, ni senefenw, be soro yen kosebe.", 0.5),
    ("Mali ye tariku jamana ye, min nyesinna a ka sini ma.", 0.0),
]

OUTPUT = Path(__file__).parent.parent / "public" / "demo-voice.wav"

# Speaking rate: < 1.0 = slower/clearer, > 1.0 = faster
SPEAKING_RATE = 0.85

print("Loading facebook/mms-tts-bam ...")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-bam")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"  Device: {device}")
model = VitsModel.from_pretrained("facebook/mms-tts-bam").to(device)
model.eval()

sr = model.config.sampling_rate
all_audio = []

for i, (text, pause) in enumerate(SENTENCES):
    print(f"  [{i+1}/{len(SENTENCES)}] {text[:50]}...")
    tokens = tokenizer(text, return_tensors="pt").to(device)
    with torch.no_grad():
        output = model(**tokens, speaking_rate=SPEAKING_RATE)
    wav = output.waveform[0].cpu().numpy()
    all_audio.append(wav)
    # Add silence pause
    if pause > 0:
        silence = np.zeros(int(sr * pause))
        all_audio.append(silence)

# Concatenate all segments
full_audio = np.concatenate(all_audio)
dur = len(full_audio) / sr

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
sf.write(str(OUTPUT), full_audio, sr)

print(f"\n  Saved: {OUTPUT}")
print(f"  Duration: {dur:.1f}s | Sample rate: {sr}Hz | Size: {OUTPUT.stat().st_size / 1024:.0f}KB")
print(f"  Sentences: {len(SENTENCES)} | Speaking rate: {SPEAKING_RATE}")
print("\nDemo voice ready!")
