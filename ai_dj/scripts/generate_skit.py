# scripts/generate_skit.py
"""Enhanced TTS generation script for Lucy AI‑DJ.

Features added:
- Multi‑voice support (lucy, caller, announcer, robotic, deep).
- SSML handling – the ``script`` argument can contain full SSML markup.
- Loudness normalization (LUFS) via ffmpeg.
- Optional background bed music mixing.

The script is invoked by the ``/skit`` API endpoint:
    python generate_skit.py "<topic>" "<voice>"
It creates a final ``.wav`` file in the ``skits/`` directory named
``<topic>.wav`` (spaces are replaced with underscores).
"""

import os
import sys
import asyncio
import aiohttp
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
import argparse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
SKITS_DIR = BASE_DIR / "skits"
BED_DIR = SKITS_DIR / "beds"
DEFAULT_BED = BED_DIR / "soft_ambient.mp3"  # optional background music

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CONSENT_DB_PATH = BASE_DIR / "data" / "consent.db"

if not ELEVENLABS_API_KEY:
    raise RuntimeError("ELEVENLABS_API_KEY not set in environment")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in environment")

# Mapping from logical voice names to ElevenLabs voice IDs (placeholder IDs)
VOICE_MAP = {
    "lucy": "EXAVITQu4vr4xnSDxMaL",
    "caller": "voice_caller_id",
    "announcer": "voice_announcer_id",
    "robotic": "voice_robotic_id",
    "deep": "voice_deep_id",
}

# ---------------------------------------------------------------------------
# OpenAI helper – generate the raw script (or SSML) for the skit
# ---------------------------------------------------------------------------
import openai
openai.api_key = OPENAI_API_KEY

async def generate_skit_script(topic: str) -> str:
    """Generate a short skit script using OpenAI (GPT‑4o).
    The model is instructed to output SSML when possible.
    """
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a witty radio host. Write a short (30‑60 s) audio skit about the given topic. Return the result as SSML wrapped in <speak> tags, using voice tags where appropriate. You may include <break>, <emphasis>, <prosody> etc."},
            {"role": "user", "content": f"Write a skit about: {topic}"},
        ],
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()

# ---------------------------------------------------------------------------
# ElevenLabs TTS – accept raw SSML text
# ---------------------------------------------------------------------------
async def synthesize_text(text: str, voice_name: str, output_mp3: Path) -> None:
    """Send SSML text to ElevenLabs and store the resulting MP3.
    ``voice_name`` must be a key in ``VOICE_MAP``.
    """
    voice_id = VOICE_MAP.get(voice_name, VOICE_MAP["lucy"])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        "model_id": "eleven_multilingual_v2",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"ElevenLabs TTS failed {resp.status}: {body}")
            with open(output_mp3, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024):
                    f.write(chunk)

# ---------------------------------------------------------------------------
# Post‑processing helpers
# ---------------------------------------------------------------------------
def _run_ffmpeg(args: list) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr}")

def normalize_loudness(input_wav: Path, output_wav: Path) -> None:
    """Apply LUFS loudness normalization using ffmpeg's ``loudnorm`` filter."""
    _run_ffmpeg(["ffmpeg", "-y", "-i", str(input_wav), "-af", "loudnorm", str(output_wav)])

def mix_with_background(voice_wav: Path, background_wav: Path, output_wav: Path) -> None:
    """Mix the voice track with a background bed using ffmpeg.
    The ``amix`` filter balances volumes.
    """
    filter_complex = "amix=inputs=2:duration=first:dropout_transition=2"
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", str(voice_wav), "-i", str(background_wav),
        "-filter_complex", filter_complex, str(output_wav)
    ])

# ---------------------------------------------------------------------------
# Consent logging (unchanged from original script)
# ---------------------------------------------------------------------------
def log_consent(skit_filename: str, user_id: str = None, consent: bool = True) -> None:
    conn = sqlite3.connect(CONSENT_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO consent_log (skit, timestamp, user_id, consent) VALUES (?, ?, ?, ?)",
        (skit_filename, datetime.utcnow().isoformat(), user_id, int(consent))
    )
    conn.commit()
    conn.close()
    print(f"Logged consent for {skit_filename}")

# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------
async def main(topic: str, voice: str, output_dir: Path) -> None:
    # 1. Generate script (SSML) via OpenAI
    script = await generate_skit_script(topic)
    # 2. Save the script for debugging (optional)
    script_path = output_dir / f"{topic.replace(' ', '_')}_script.txt"
    script_path.write_text(script, encoding="utf-8")
    # 3. Synthesize to MP3 using ElevenLabs
    mp3_path = output_dir / f"{topic.replace(' ', '_')}.mp3"
    await synthesize_text(script, voice, mp3_path)
    # 4. Convert MP3 to WAV (intermediate)
    wav_intermediate = output_dir / f"{topic.replace(' ', '_')}_raw.wav"
    _run_ffmpeg(["ffmpeg", "-y", "-i", str(mp3_path), str(wav_intermediate)])
    # 5. Loudness normalization
    wav_normalized = output_dir / f"{topic.replace(' ', '_')}_norm.wav"
    normalize_loudness(wav_intermediate, wav_normalized)
    # 6. Optional background mix
    final_wav = output_dir / f"{topic.replace(' ', '_')}.wav"
    if DEFAULT_BED.is_file():
        mix_with_background(wav_normalized, DEFAULT_BED, final_wav)
    else:
        wav_normalized.rename(final_wav)
    # 7. Clean up intermediates
    for p in [mp3_path, wav_intermediate, wav_normalized]:
        if p.exists():
            p.unlink()
    # 8. Log consent (default True)
    log_consent(final_wav.name)
    print(f"Generated skit audio: {final_wav}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a skit audio file.")
    parser.add_argument("topic", help="The skit topic / script name")
    parser.add_argument("voice", nargs="?", default="lucy", help="Voice name (lucy, caller, announcer, robotic, deep)")
    args = parser.parse_args()
    skit_dir = BASE_DIR / "skits"
    os.makedirs(skit_dir, exist_ok=True)
    asyncio.run(main(args.topic, args.voice, skit_dir))
