from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict
import numpy as np
import os

app = FastAPI()

class PromptState(BaseModel):
	P_t: Dict[str, float]
	T_t: Dict[str, float] | None = None
	C_t: Dict[str, float] | None = None
	S_t: Dict[str, float] | None = None

# simple weights
ETA = float(os.environ.get("EP_ETA", "0.1"))
LAMBDA = float(os.environ.get("EP_LAMBDA", "0.01"))
W_perf = {"cpu": 1.0, "mem": 0.5}

@app.post("/prompt/update")
async def update_prompt(state: PromptState):
	P = state.P_t.copy()
	# compute grad placeholder: negative of C_t if present
	grad = {}
	if state.C_t:
		for k, v in state.C_t.items():
			grad[k] = -v
	# apply update
	for k, val in P.items():
		g = grad.get(k, 0.0)
		perf_penalty = 0.0
		if state.T_t and k in W_perf:
			perf_penalty = LAMBDA * state.T_t.get(k, 0.0) * W_perf[k]
		P[k] = val + ETA * g - perf_penalty
	return {"P_t1": P}

if __name__ == '__main__':
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8014)


@app.get("/health")
async def health():
	return {"status": "ok", "service": "evolutionary-prompt"}
