"""
Generate the demo voice sample for the landing page.
Uses the ekodi TTS endpoint to synthesize Bamanankan speech.

Usage:
  python generate-demo-voice.py                    # uses local backend (localhost:8000)
  python generate-demo-voice.py --url https://api.ekodi.ai
  python generate-demo-voice.py --api-key ek-xxx   # uses API key auth
"""

import argparse
import requests
import sys
from pathlib import Path

# The demo AI response text in Bamanankan
DEMO_TEXT = "I ni ce! Bamako sigida camanw ka ɲi kosɛbɛ. Hamdallaye, ACI 2000, ani Badalabougou ye sigida ɲumanw ye."

OUTPUT_PATH = Path(__file__).parent.parent / "public" / "demo-voice.wav"


def generate_with_api_key(base_url: str, api_key: str):
    """Use /api/v1/tts with X-API-Key auth."""
    url = f"{base_url.rstrip('/')}/api/v1/tts"
    print(f"POST {url}")
    resp = requests.post(url, json={"text": DEMO_TEXT}, headers={"X-API-Key": api_key})
    resp.raise_for_status()
    return resp.content


def generate_with_jwt(base_url: str, email: str, password: str):
    """Login then use /tts with JWT auth."""
    login_url = f"{base_url.rstrip('/')}/auth/login"
    print(f"Logging in at {login_url}...")
    login_resp = requests.post(login_url, json={"email": email, "password": password})
    login_resp.raise_for_status()
    token = login_resp.json()["access_token"]

    tts_url = f"{base_url.rstrip('/')}/tts"
    print(f"POST {tts_url}")
    resp = requests.post(tts_url, json={"text": DEMO_TEXT}, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.content


def main():
    parser = argparse.ArgumentParser(description="Generate demo voice for landing page")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--api-key", help="API key for /api/v1/tts")
    parser.add_argument("--email", help="Login email for JWT auth")
    parser.add_argument("--password", help="Login password for JWT auth")
    args = parser.parse_args()

    try:
        if args.api_key:
            wav_data = generate_with_api_key(args.url, args.api_key)
        elif args.email and args.password:
            wav_data = generate_with_jwt(args.url, args.email, args.password)
        else:
            # Try unauthenticated (for local dev with auth disabled)
            url = f"{args.url.rstrip('/')}/api/v1/tts"
            print(f"POST {url} (no auth)")
            resp = requests.post(url, json={"text": DEMO_TEXT})
            resp.raise_for_status()
            wav_data = resp.content

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_bytes(wav_data)
        size_kb = len(wav_data) / 1024
        print(f"\nSaved {size_kb:.0f}KB -> {OUTPUT_PATH}")
        print("Demo voice ready!")

    except requests.exceptions.ConnectionError:
        print(f"\nError: Cannot connect to {args.url}")
        print("Make sure the backend is running.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"\nError: {e.response.status_code} - {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
