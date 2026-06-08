import os
import asyncio
import aiohttp
from deepgram import Deepgram

# Deepgram STT async wrapper

def get_deepgram_client():
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY not set in environment")
    return Deepgram(api_key)

async def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file (wav/ogg/mp3) using Deepgram.
    Returns the transcript text.
    """
    client = get_deepgram_client()
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as audio:
            source = {"buffer": audio.read(), "mimetype": "audio/wav"}
            options = {"punctuate": True, "model": "general"}
            response = await client.transcription.prerecorded(source, options)
            return response.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")

# Simple test runner
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ai_handler.py <audio_file>")
        sys.exit(1)
    transcript = asyncio.run(transcribe_audio(sys.argv[1]))
    print("Transcript:", transcript)
