# FastAPI app for ergonomics_service

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal
import uuid
import datetime
import json
import os

app = FastAPI(title="Ergonomics Service", version="v0.1")

# Path to DataVault (using SQLite for simplicity)
DB_PATH = os.getenv("DATAVAULT_PATH", "../datavault/luceneverse_memory.db")

class DeepWorkProfile(BaseModel):
    deep_work_mode: Literal["Monastic", "Bimodal", "Rhythmic", "Journalistic"]
    maker_hours: List[str]
    manager_hours: List[str]
    do_not_disturb_windows: List[str] = Field(default_factory=list)
    meeting_cluster_policy: Literal["post_lunch", "pre_lunch", "none"] = "post_lunch"
    seven_bs: List[Literal["bits","budgets","blocks","batches","buffers","bounds","barriers"]] = Field(default_factory=list)

class ScheduleResponse(BaseModel):
    date: str
    blocks: List[dict]

# In‑memory store for demo (real implementation would write to DataVault)
_profiles = {}

@app.post("/schedule/deep-work-profile", response_model=dict)
def create_profile(profile: DeepWorkProfile):
    profile_id = str(uuid.uuid4())
    profiles[profile_id] = profile.dict()
    # TODO: write immutable record to DataVault with hash chain
    return {"profile_id": profile_id}

@app.get("/schedule/today", response_model=ScheduleResponse)
def get_today_schedule():
    # Simple deterministic schedule for demo purposes
    today = datetime.date.today().isoformat()
    blocks = []
    # Example: maker block 08:00‑12:00, manager block 13:00‑17:00
    for pid, p in profiles.items():
        for hrs in p["maker_hours"]:
            start, end = hrs.split("-")
            blocks.append({"type": "maker", "start": start, "end": end, "profile_id": pid})
        for hrs in p["manager_hours"]:
            start, end = hrs.split("-")
            blocks.append({"type": "manager", "start": start, "end": end, "profile_id": pid})
    return {"date": today, "blocks": blocks}
