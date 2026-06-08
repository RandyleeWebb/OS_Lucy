import os
import json
import datetime
from typing import Dict
from bus import publish
from tts import ElevenLabsTTS
from script_utils import normalize_script
from voice_markup import apply_voice_markup
from audio_processing import loudnorm_normalize, mix_with_background, convert_to_mp2


def get_output_paths():
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
    base_dir = '/app/outgoing/skits'
    os.makedirs(base_dir, exist_ok=True)
    wav_path = os.path.join(base_dir, f'skit_{timestamp}.wav')
    mp2_path = os.path.join(base_dir, f'skit_{timestamp}.mp2')
    return wav_path, mp2_path

async def process_skit(payload: Dict) -> None:
    """Full skit generation pipeline.
    Payload example: {"topic": "traffic", "host": "HOST_SARAH", "caller": "CALLER_TOM"}
    """
    # 1. Generate raw script (placeholder – in real system this would be more complex)
    raw_script = f"<HOST_SARAH> Good morning, this is {payload.get('host', 'HOST_SARAH')}.\n<CALLER_TOM> Hi, I need traffic updates."

    # 2. Normalize script
    normalized = normalize_script(raw_script)

    # 3. Apply voice markup (SSML/XML for ElevenLabs)
    ssml = apply_voice_markup(normalized)

    # 4. Synthesize audio via ElevenLabs
    tts = ElevenLabsTTS()
    voice_id = "YOUR_DEFAULT_VOICE_ID"  # TODO: map host/caller to specific voice IDs
    audio_bytes = await tts.synthesize(ssml, voice_id, params={})

    # 5. Write raw WAV to file
    wav_path, mp2_path = get_output_paths()
    with open(wav_path, 'wb') as f:
        f.write(audio_bytes)

    # 6. Loudness normalization
    loudnorm_normalize(wav_path)

    # 7. Mix with background bed (assumes bed file at /app/beds/default.wav)
    mix_with_background(wav_path, '/app/beds/default.wav')

    # 8. Convert to MP2 for broadcast
    convert_to_mp2(wav_path, mp2_path)

    # 9. Publish success event
    await publish('skit:generated', {'path': mp2_path})
