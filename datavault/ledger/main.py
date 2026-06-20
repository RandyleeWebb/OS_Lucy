from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import aiosqlite
import hashlib
import json
import os

SERVICE_NAME = "ledger"
DB_PATH = "/data/datavault.db"

app = FastAPI(title=f"Lucy {SERVICE_NAME}")

http_requests_total = Counter(
    f"{SERVICE_NAME}_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"]
)

@app.on_event("startup")
async def startup():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ledger (
                sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                intent_hash TEXT NOT NULL,
                safeguard_decision TEXT NOT NULL,
                execution_metrics TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                curr_hash TEXT NOT NULL,
                signature TEXT NOT NULL
            )
        """)
        await db.commit()

@app.get("/health")
async def health():
    http_requests_total.labels("GET", "/health", 200).inc()
    return {"up": True, "service": SERVICE_NAME, "version": "0.1.0"}

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

class VaultEntry(BaseModel):
    intent_id: str
    timestamp: str
    actor: str = "orchestrator"
    intent_hash: str = ""
    safeguard_decision: str = ""
    execution_metrics: str = ""
    signature: str = "unsigned"

@app.post("/vault/append")
async def append(entry: VaultEntry):
    http_requests_total.labels("POST", "/vault/append", 200).inc()
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Get previous hash
        async with db.execute("SELECT curr_hash FROM ledger ORDER BY sequence_id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            prev_hash = row[0] if row else "0" * 64

        # Compute current hash
        entry_dict = entry.model_dump()
        entry_dict["prev_hash"] = prev_hash
        data_string = json.dumps(entry_dict, sort_keys=True)
        curr_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()

        await db.execute("""
            INSERT INTO ledger (
                intent_id, timestamp, actor, intent_hash, safeguard_decision, 
                execution_metrics, prev_hash, curr_hash, signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.intent_id, entry.timestamp, entry.actor, entry.intent_hash,
            entry.safeguard_decision, entry.execution_metrics, prev_hash, curr_hash, entry.signature
        ))
        await db.commit()
        
        # Return inserted id
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            row = await cursor.fetchone()
            sequence_id = row[0]

    return {"status": "appended", "sequence_id": sequence_id, "curr_hash": curr_hash}

@app.get("/vault/entry/{seq_id}")
async def get_entry(seq_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM ledger WHERE sequence_id = ?", (seq_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Entry not found")
            return dict(row)

@app.get("/vault/entries")
async def get_entries(limit: int = 1000, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT sequence_id, curr_hash FROM ledger ORDER BY sequence_id ASC LIMIT ? OFFSET ?", (limit, offset)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
