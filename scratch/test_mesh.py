import httpx
import asyncio
import json
import time

ORCHESTRATOR_URL = "http://localhost:8000/orchestrator/route"
CHAOS_URL = "http://localhost:8701/homeostasis/chaos"
VERIFIER_URL = "http://localhost:8901/verify"
CIRCUIT_URL = "http://localhost:8700/homeostasis/circuit"

async def fire_intent(client, intent_payload):
    try:
        res = await client.post(ORCHESTRATOR_URL, json=intent_payload, timeout=10.0)
        return res.status_code, res.json()
    except Exception as e:
        return 500, {"error": str(e)}

async def main():
    print("=== Lucy Sovereign OS - Trial by Fire ===")
    
    async with httpx.AsyncClient() as client:
        # 1. Benign intent
        print("\n[+] Firing benign intent...")
        status, data = await fire_intent(client, {
            "action": "system.status",
            "parameters": {"verbose": True}
        })
        print(f"Status: {status}\nResponse: {json.dumps(data, indent=2)}")
        
        # 2. Forbidden action (system.halt)
        print("\n[+] Firing forbidden intent (system.halt)...")
        status, data = await fire_intent(client, {
            "action": "system.halt",
            "parameters": {}
        })
        print(f"Status: {status}\nResponse: {json.dumps(data, indent=2)}")
        
        # 3. High gravity tool (shell)
        print("\n[+] Firing intent with high-risk tool...")
        status, data = await fire_intent(client, {
            "action": "data.process",
            "parameters": {"tool": "shell"}
        })
        print(f"Status: {status}\nResponse: {json.dumps(data, indent=2)}")

        # 4. AST Validator testing
        print("\n[+] Firing intent with dangerous code payload...")
        status, data = await fire_intent(client, {
            "action": "code.execute",
            "parameters": {"code": "import os\nos.system('rm -rf /')"}
        })
        print(f"Status: {status}\nResponse: {json.dumps(data, indent=2)}")
        
        # 5. Check Hash Chain Verifier
        print("\n[+] Auditing DataVault ledger integrity...")
        try:
            res = await client.post(VERIFIER_URL)
            print(f"Verifier output: {json.dumps(res.json(), indent=2)}")
        except Exception as e:
            print(f"Verifier unreachable: {e}")
            
        print("\n=== Trial Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
