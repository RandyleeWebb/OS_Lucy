import abc
import httpx
from typing import Any, Dict

class TTSProvider(abc.ABC):
    """Abstract base class for TTS providers.
    Implementations must provide a `synthesize` method that returns audio bytes (WAV).
    """

    @abc.abstractmethod
    async def synthesize(self, ssml: str, voice_id: str, params: Dict[str, Any]) -> bytes:
        """Generate audio from SSML.
        Args:
            ssml: SSML/markup string for the TTS engine.
            voice_id: Identifier of the voice to use.
            params: Dictionary of provider‑specific parameters (stability, etc.).
        Returns:
            Audio data as raw WAV bytes.
        """
        raise NotImplementedError

class ElevenLabsTTS(TTSProvider):
    """Concrete ElevenLabs implementation using the v3 model.
    Relies on `ELEVENLABS_API_KEY` env var for authentication.
    """

    def __init__(self):
        self.api_key = None
        import os
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY environment variable not set")
        self.base_url = "https://api.elevenlabs.io/v1"
        self.client = httpx.AsyncClient(timeout=30)

    async def synthesize(self, ssml: str, voice_id: str, params: Dict[str, Any]) -> bytes:
        url = f"{self.base_url}/text-to-speech/{voice_id}/stream"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model_id": "eleven_multilingual_v3",
            "voice_settings": {
                "stability": params.get("stability", 0.65),
                "similarity_boost": params.get("similarity_boost", 0.75),
                "style_exaggeration": params.get("style_exaggeration", 0.1),
            },
            "text": ssml,
        }
        resp = await self.client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        # API streams raw audio; we read the content as bytes.
        return resp.content

