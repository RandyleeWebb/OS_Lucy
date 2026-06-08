import requests
import os

PROMPT_URL = os.environ.get("PROMPT_URL", "http://evolutionary-prompt:8014/prompt/update")

def update(P_t: dict, T_t: dict | None = None, C_t: dict | None = None, S_t: dict | None = None):
	try:
		r = requests.post(PROMPT_URL, json={"P_t": P_t, "T_t": T_t, "C_t": C_t, "S_t": S_t}, timeout=5)
		return r.json()
	except Exception as e:
		return {"P_t1": P_t}
