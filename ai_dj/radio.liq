# radio.liq
# Liquidsoap configuration for Lucy AI‑DJ
# ---------------------------------------------------
# 1. Music playlist (existing music library)
# Adjust the path if your music folder differs.
music = playlist("docker/navidrome/music", reload_mode="watch")
# 1b. Lucy voice clips (pre‑recorded/TTs)
voice_clips = playlist("voice/lucy/all", reload_mode="watch")
# 2. AI skit playlist – watches the ready queue directory
skits = playlist("skits/ready", reload_mode="watch")

# 3. AI stream with ducking – smooth_add mixes skits over music
ai_stream = smooth_add(
  p=0.8,
  normal=music,
  special=skits
)

# 4. Dynamic trigger logic – reads the trigger file written by the worker
# Dynamic trigger logic removed for now – always returns silence.
ai_dynamic = blank()
generated = playlist("generated", reload_mode="watch")

# ai_dynamic already defined above

# 5. Combine everything – fallback order gives priority to dynamic inserts
final = fallback([generated, ai_dynamic, ai_stream, voice_clips, music])

# 6. Stream out to Icecast (adjust host/port/password if needed)
output.icecast(%mp3, host="icecast", port=8000, password="hackme", mount="lucy.mp3", final)
