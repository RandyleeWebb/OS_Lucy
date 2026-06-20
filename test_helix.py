import urllib.request
import urllib.error
import json
import time

HELIX_URL = "http://localhost:3000/api/helix/tool-use"

# 1. We will test fs_write to create a dummy file
test_payload = {
    "toolId": "fs_write",
    "params": {
        "path": "D:/lucy ecosystem/OS_Lucy's/lucy_test_patch.txt",
        "content": "Hello from Lucy Core! If you are reading this, Helix successfully executed an fs_write command on the host machine. Phase 1 is a success."
    }
}

req = urllib.request.Request(
    HELIX_URL, 
    data=json.dumps(test_payload).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'x-helix-signature': 'lucy-auth-token'}
)

try:
    print("[Lucy Core] Sending fs_write payload to Helix...")
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode('utf-8'))
    print(f"[Helix Response] {json.dumps(result, indent=2)}")
    print("\nSUCCESS! Helix's DevOps hands are active.")
except urllib.error.URLError as e:
    print(f"[Error] Failed to connect to Helix. Is the server running? Details: {e}")
except Exception as e:
    print(f"[Error] An unexpected error occurred: {e}")
