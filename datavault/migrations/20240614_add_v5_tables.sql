-- SQLite migrations for Lucy OS v5 additions

-- 1. Ergonomics profiles table
CREATE TABLE IF NOT EXISTS ergonomics_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL UNIQUE,
    payload JSON NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    hash TEXT NOT NULL,
    signature TEXT NOT NULL
);

-- 2. Tasks table (GTD/Eisenhower/Kanban)
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    context TEXT NOT NULL,
    quadrant TEXT CHECK(quadrant IN ('Q1','Q2','Q3','Q4')),
    status TEXT CHECK(status IN ('todo','in_progress','review','done')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    hash TEXT NOT NULL,
    signature TEXT NOT NULL
);

-- 3. Delegation logs table
CREATE TABLE IF NOT EXISTS delegation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    parameters JSON NOT NULL,
    suitability_score REAL NOT NULL,
    roi_score REAL NOT NULL,
    delegation_level INTEGER NOT NULL,
    recommended_mode TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    hash TEXT NOT NULL,
    signature TEXT NOT NULL
);

-- 4. Prompt sessions table
CREATE TABLE IF NOT EXISTS prompt_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    framework TEXT NOT NULL,
    raw_input TEXT NOT NULL,
    output TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    hash TEXT NOT NULL,
    signature TEXT NOT NULL
);

-- 5. Host signals table
CREATE TABLE IF NOT EXISTS host_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    metadata JSON NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    hash TEXT NOT NULL,
    signature TEXT NOT NULL
);
