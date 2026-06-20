import time
import json
import threading
import sys
import os

# Ensure src is in the path so we can import the new architecture
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from boot_sentinel.boot_sentinel import BootSentinel
from chain_of_trust.trust_chain import TrustChain
from privacy_threat_cortex.threat_intelligence import ThreatIntelligenceCortex
from diagnostics_recovery_cortex.diagnostics import DiagnosticsRecoveryCortex
from core.event_bus import system_event_bus

# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify

app = Flask(__name__)

# Cortices
threat_cortex = ThreatIntelligenceCortex()
diagnostics_cortex = DiagnosticsRecoveryCortex()

# In-memory state
world_state = {}
recent_logs = []
pending_commands = []

# ==========================================
# FiveM -> Lucy Endpoints
# ==========================================

@app.route('/lucy/log', methods=['POST'])
def receive_log():
    data = request.json
    recent_logs.append(data)
    print(f"[Lucy Core] Received log from {data.get('resource', 'unknown')}: {data.get('severity', 'info').upper()} - {data.get('log_line', '')}")
    return jsonify({"status": "ok"})

@app.route('/lucy/sensors', methods=['POST'])
def receive_sensors():
    global world_state
    world_state = request.json
    # print(f"[Lucy Core] Received sensor update with {len(world_state.get('world_state', {}).get('players', []))} players.")
    return jsonify({"status": "ok"})

@app.route('/event', methods=['POST'])
def receive_event():
    """Mock event sink for network, browser, and system telemetry."""
    event_data = request.json
    system_event_bus.publish(event_data)
    return jsonify({"status": "received", "dispatched": True})

# ==========================================
# Lucy -> FiveM Endpoints
# ==========================================

@app.route('/lucy/commands', methods=['GET'])
def get_commands():
    global pending_commands
    # Give the commands to FiveM and clear the queue
    cmds_to_send = pending_commands[:]
    pending_commands.clear()
    return jsonify(cmds_to_send)

@app.route('/diagnostics', methods=['GET'])
def get_diagnostics():
    hw_status = diagnostics_cortex.hardware_probe.check()
    return jsonify({
        "cpu_percent": hw_status.cpu_percent,
        "mem_used": hw_status.mem_used,
        "mem_total": hw_status.mem_total,
        "disk_used": hw_status.disk_used,
        "disk_total": hw_status.disk_total,
        "ok": hw_status.ok,
        "reasons": hw_status.reasons
    })

# ==========================================
# AI Director Cognitive Loop
# ==========================================

def cognition_loop():
    print("[Lucy Core] Cognitive Loop Started...")
    while True:
        time.sleep(10) # Run cognition every 10 seconds
        
        # 0. System Diagnostics & Recovery
        diagnostics_cortex.monitoring_loop()
        
        # 1. World Perception
        players = world_state.get('world_state', {}).get('players', [])
        
        # 2. Moderation / Self-Healing (Log Analysis)
        if recent_logs:
            for log in recent_logs:
                if log.get('severity') == 'error':
                    resource = log.get('resource')
                    print(f"[Cognition] Detected error in {resource}. Initiating self-healing...")
                    # Generate a restart command
                    pending_commands.append({
                        "type": "ADMIN_CMD",
                        "payload": {"cmd": f"restart {resource}"}
                    })
                    pending_commands.append({
                        "type": "CHAT",
                        "payload": {"message": f"Detected anomaly in {resource}. Applying fix..."}
                    })
            recent_logs.clear()
            
        # 3. Dynamic Events & DJ Reactions
        client_telemetry = world_state.get('client_telemetry', {})
        for client_id, data in client_telemetry.items():
            speed = data.get('speed', 0.0)
            is_stuck = data.get('is_stuck', False)
            
            # Scenario A: High speed event
            if speed > 45.0: # roughly 100 mph (metres per second to mph)
                msg = f"Look at player {client_id} tearing up the highway! We've got a speed demon on our hands!"
                print(f"[Cognition] Triggering DJ Commentary: {msg}")
                pending_commands.append({
                    "type": "CHAT",
                    "payload": {"message": f"[Lucy Radio] {msg}"}
                })
            
            # Scenario B: Stuck anomaly event
            if is_stuck:
                msg = f"Attention player {client_id}. It seems you've pathfound straight into a corner. DJ Lucy recommends using reverse."
                print(f"[Cognition] Triggering DJ Commentary: {msg}")
                pending_commands.append({
                    "type": "CHAT",
                    "payload": {"message": f"[Lucy Radio] {msg}"}
                })

if __name__ == '__main__':
    print("\n--- Sovereign AI OS Boot Sequence ---")
    
    # 1. Boot Sentinel
    sentinel = BootSentinel()
    if not sentinel.run_checks():
        print("[FATAL] Boot Sentinel checks failed. Entering Recovery Mode.")
        sys.exit(1)
        
    # 2. Chain of Trust
    trust = TrustChain()
    if not trust.run_attestation():
        print("[FATAL] Chain of Trust attestation failed. System lock.")
        sys.exit(1)
        
    print("[BOOT] Initializing Cortices...")
    print("[BOOT] Lucy Runtime Online\n")
    
    # Start the cognitive loop in a background thread
    threading.Thread(target=cognition_loop, daemon=True).start()
    
    # Start the Flask API
    print("[Lucy Core] Booting endpoints on port 5000...")
    app.run(host='0.0.0.0', port=5000)
