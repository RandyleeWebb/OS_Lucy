import urllib.request
import urllib.error
import json

URL = "http://localhost:3000/api/dj/announce"

payload = {
    "text": "This is Lucy Radio live from the Helix OS container.",
    "voice": "lucy"
}

req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    print("[Test DJ] Sending TTS announcement request to Helix...")
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode('utf-8'))
    print(f"[DJ Response] {json.dumps(result, indent=2)}")
except urllib.error.URLError as e:
    print(f"[Error] Failed to connect: {e}")
except Exception as e:
    print(f"[Error] Unexpected error: {e}")
