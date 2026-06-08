-- Migration: initial schema for Lucy runtime security

-- Table: audit_events
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    action TEXT NOT NULL,
    capability TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW','DENY')),
    resource TEXT,
    reason TEXT
);

-- Table: capabilities
CREATE TABLE IF NOT EXISTS capabilities (
    cap_id TEXT PRIMARY KEY,
    scopes TEXT NOT NULL -- JSON array of strings
);

-- Table: role_assignments
CREATE TABLE IF NOT EXISTS role_assignments (
    role TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    cap_id TEXT NOT NULL,
    PRIMARY KEY (role, agent_id),
    FOREIGN KEY (cap_id) REFERENCES capabilities(cap_id)
);

-- Table: workspace_map
CREATE TABLE IF NOT EXISTS workspace_map (
    path TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    metadata TEXT -- JSON blob
);

-- Table: long_term_memory
CREATE TABLE IF NOT EXISTS long_term_memory (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Table: proposals
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    json TEXT NOT NULL, -- full proposal JSON blob
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING','APPROVED','DENIED'))
);

-- Table: decisions
CREATE TABLE IF NOT EXISTS decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    reason TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(proposal_id)
);

-- Table: archive_meta
CREATE TABLE IF NOT EXISTS archive_meta (
    table_name TEXT PRIMARY KEY,
    archived_until TEXT NOT NULL
);
