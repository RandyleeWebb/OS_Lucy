# FastAPI app for productivity_service

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
import uuid
import datetime
import json
import os

app = FastAPI(title="Productivity Service", version="v0.1")

DB_PATH = os.getenv("DATAVAULT_PATH", "../datavault/luceneverse_memory.db")

class TaskCreate(BaseModel):
    description: str
    context: Literal["@computer", "@code", "@calls", "@errands", "@waiting", "@low-energy"]

class TaskPrioritize(BaseModel):
    uuid: str
    quadrant: Literal["Q1", "Q2", "Q3", "Q4"]

class KanbanResponse(BaseModel):
    columns: dict

# In‑memory store for demo
tasks = {}

@app.post("/tasks/capture", response_model=dict)
def capture_task(task: TaskCreate):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "description": task.description,
        "context": task.context,
        "status": "todo",
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    # TODO: write immutable record to DataVault
    return {"uuid": task_id}

@app.post("/tasks/prioritize", response_model=dict)
def prioritize_task(prio: TaskPrioritize):
    t = tasks.get(prio.uuid)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    t["quadrant"] = prio.quadrant
    # TODO: update DataVault entry
    return {"uuid": prio.uuid, "quadrant": prio.quadrant}

@app.get("/tasks/kanban", response_model=KanbanResponse)
def get_kanban():
    # Simple grouping by status
    columns = {"todo": [], "in_progress": [], "review": [], "done": []}
    for uid, t in tasks.items():
        columns[t["status"]].append({"uuid": uid, "description": t["description"]})
    return {"columns": columns}
