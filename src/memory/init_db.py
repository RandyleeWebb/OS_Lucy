import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'lucy.db'))

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# assets table stores generated media metadata
cur.execute('''
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,          -- e.g., 'skit', 'song', 'mix'
    path TEXT NOT NULL,
    prompt TEXT,                -- original generation prompt / dialog
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# plans table stores generated plans
cur.execute('''
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# logs table stores step execution logs
cur.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,
    step_index INTEGER,
    service_name TEXT,
    endpoint TEXT,
    request_payload TEXT,
    response_status INTEGER,
    response_body TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_id) REFERENCES plans(id)
)''')

conn.commit()
conn.close()
