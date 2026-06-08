"""Homeostasis (System-3) microservice

Runs as a FastAPI service with a background loop that polls telemetry from
DataVault/PerfMon, computes a simple deviation metric and injects
proactive tasks into the orchestrator when necessary. All decisions are
logged to the DataVault for auditability.
"""

import asyncio
import os
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException

APP = FastAPI(title="homeostasis")

# Configuration from environment
POLL_INTERVAL = int(os.environ.get("PEPA_POLL_INTERVAL", "30"))
THRESHOLD = float(os.environ.get("PEPA_THRESHOLD", "0.5"))
DATAVAULT_LOG = os.environ.get("DATAVAULT_URL", "http://datavault:8012/log")
DATAVAULT_ENTRIES = os.environ.get("DATAVAULT_ENTRIES", "http://datavault:8012/entries")
ORCHESTRATOR_INJECT = os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8020/inject_proactive")

# In-memory state exposed over /drives
STATE: Dict[str, Any] = {
	"last_deviation": 0.0,
	"last_drives": {},
	"last_injection": None,
	"runs": 0,
}


async def fetch_recent_perfmon() -> Dict[str, float]:
	"""Query datavault for recent perfmon entries and synthesize telemetry.

	The PerfMon agent posts cpu/mem samples. We map them into a
	small telemetry vector used by the homeostatic evaluator.
	"""
	async with httpx.AsyncClient(timeout=10.0) as client:
		try:
			resp = await client.get(f"{DATAVAULT_ENTRIES}?source=perfmon&limit=20")
			resp.raise_for_status()
			entries = resp.json()
		except Exception:
			entries = []

	# compute simple aggregates
	cpu_vals = []
	mem_vals = []
	for e in entries:
		payload = e.get("payload") if isinstance(e, dict) else None
		if not payload:
			continue
		cpu = payload.get("cpu")
		mem = payload.get("mem")
		if isinstance(cpu, (int, float)):
			cpu_vals.append(float(cpu))
		if isinstance(mem, (int, float)):
			mem_vals.append(float(mem))

	avg_cpu = sum(cpu_vals) / len(cpu_vals) / 100.0 if cpu_vals else 0.0
	avg_mem = sum(mem_vals) / len(mem_vals) / 100.0 if mem_vals else 0.0

	telemetry = {
		"battery_level": 1.0,  # no battery in this demo
		"system_risk": min(max(avg_mem, 0.0), 1.0),
		"entropy_debt": min(max(avg_cpu, 0.0), 1.0),
		"task_utility": max(0.0, 1.0 - avg_cpu),
	}
	return telemetry


def evaluate_deviation(telemetry: Dict[str, float], traits: Optional[Dict[str, float]] = None) -> float:
	traits = traits or {}
	weights = [
		traits.get("conscientiousness", 0.5) * 0.8,
		(1.0 - traits.get("conscientiousness", 0.5)) * 0.9,
		traits.get("openness", 0.5) * 1.2,
		traits.get("utility_focus", 0.5) * 1.0,
	]
	drives = [
		telemetry.get("battery_level", 1.0),
		telemetry.get("system_risk", 0.0),
		telemetry.get("entropy_debt", 1.0),
		telemetry.get("task_utility", 1.0),
	]
	targets = [1.0, 0.0, 0.0, 1.0]
	dev = 0.0
	for w, d, t in zip(weights, drives, targets):
		dev += w * (d - t) ** 2
	import math

	return math.sqrt(dev)


async def log_to_datavault(entry: Dict[str, Any]):
	async with httpx.AsyncClient(timeout=10.0) as client:
		try:
			await client.post(DATAVAULT_LOG, json=entry)
		except Exception:
			# best-effort logging; don't crash the loop
			pass


async def inject_proactive_task(origin: str, intent: str, priority: int = 5, meta: Optional[Dict[str, Any]] = None):
	payload = {"origin": origin, "intent": intent, "priority": priority, "meta": meta or {}}
	# log decision to datavault
	await log_to_datavault({"source": "homeostasis", "payload": {"decision": payload}})

	# post into orchestrator
	async with httpx.AsyncClient(timeout=10.0) as client:
		try:
			resp = await client.post(ORCHESTRATOR_INJECT, json=payload)
			return {"ok": True, "status_code": resp.status_code, "response": resp.text}
		except Exception as e:
			return {"ok": False, "error": str(e)}


async def background_loop(stop_event: asyncio.Event):
	while not stop_event.is_set():
		STATE["runs"] = STATE.get("runs", 0) + 1
		telemetry = await fetch_recent_perfmon()
		deviation = evaluate_deviation(telemetry)
		STATE["last_deviation"] = deviation
		STATE["last_drives"] = telemetry
		STATE["last_run_ts"] = time.time()

		if deviation > THRESHOLD:
			STATE["last_injection"] = {"ts": time.time(), "deviation": deviation}
			# create a human-readable intent for demo purposes
			intent = "RESOLVE_UNCERTAINTY"
			resp = await inject_proactive_task("System_3_Homeostasis", intent, priority=int(deviation * 10), meta={"deviation": deviation})
			STATE.setdefault("injection_log", []).append({"intent": intent, "resp": resp, "deviation": deviation, "ts": time.time()})

		await asyncio.sleep(POLL_INTERVAL)


@APP.on_event("startup")
async def startup_event():
	APP.state._stop_event = asyncio.Event()
	APP.state._bg_task = asyncio.create_task(background_loop(APP.state._stop_event))


@APP.on_event("shutdown")
async def shutdown_event():
	APP.state._stop_event.set()
	await APP.state._bg_task


@APP.get("/health")
async def health():
	return {"ok": True}


@APP.get("/drives")
async def drives():
	return STATE


@APP.post("/inject")
async def inject(payload: Dict[str, Any], background: BackgroundTasks):
	origin = payload.get("origin", "external")
	intent = payload.get("intent", "CUSTOM")
	priority = int(payload.get("priority", 5))
	background.add_task(inject_proactive_task, origin, intent, priority, payload.get("meta"))
	return {"accepted": True}


if __name__ == "__main__":
	import uvicorn

	uvicorn.run(APP, host="0.0.0.0", port=int(os.environ.get("HOMEOSTASIS_PORT", 8030)))
