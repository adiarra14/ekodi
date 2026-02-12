#!/usr/bin/env python3
"""Quick test of the Ekodi TTS server API."""
import json
import urllib.request

BASE = "http://127.0.0.1:8000"

# Test health
print("=== Health ===")
resp = urllib.request.urlopen(f"{BASE}/health")
print(json.loads(resp.read()))

# Test TTS
print("\n=== TTS Synthesis ===")
tests = [
    "I ni ce",
    "Aw ni ce, ne togo ye Ekodi",
]
for text in tests:
    data = json.dumps({"text": text}).encode()
    req = urllib.request.Request(f"{BASE}/tts", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    wav_bytes = resp.read()
    fname = f"data/test_server_{text[:10].replace(' ', '_')}.wav"
    with open(fname, "wb") as f:
        f.write(wav_bytes)
    print(f'  "{text}" -> {fname} ({len(wav_bytes)} bytes)')

print("\nServer test OK!")
