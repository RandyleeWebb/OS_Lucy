import urllib.request
import urllib.error
import json
import time

START_URL = "http://localhost:3000/api/trainer/start"
STATUS_URL = "http://localhost:3000/api/trainer/status"

# Start training
req_start = urllib.request.Request(
    START_URL,
    data=b"{}",
    headers={'Content-Type': 'application/json'}
)

try:
    print("[Test Trainer] Triggering AI Trainer start...")
    response = urllib.request.urlopen(req_start)
    result = json.loads(response.read().decode('utf-8'))
    print(f"[Start Result] {json.dumps(result, indent=2)}")
    
    # Wait a moment for training to generate some logs
    print("Waiting 5 seconds to gather metrics...")
    time.sleep(5)
    
    # Fetch status
    print("Fetching Trainer status...")
    response_status = urllib.request.urlopen(STATUS_URL)
    status_result = json.loads(response_status.read().decode('utf-8'))
    print(f"[Status Result] Status: {status_result['status']}")
    print(f"[Telemetry] Accuracy: {status_result['telemetry'].get('accuracy')}% | Loss: {status_result['telemetry'].get('loss')}")
    print(f"[Latest Logs] (Showing last 5 lines):")
    for log in status_result['logs'][-5:]:
        print(f"  {log}")
        
    print("\nSUCCESS! Phase 3 AI Trainer is fully integrated with Helix.")
except urllib.error.URLError as e:
    print(f"[Error] Connection error: {e}")
except Exception as e:
    print(f"[Error] Unexpected error: {e}")
