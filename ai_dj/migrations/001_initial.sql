-- 001_initial.sql: create core tables for security fabric, auditing, and consent logging

-- Audit events table
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    action TEXT NOT NULL,
    capability TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    resource TEXT
);

-- Proposals table (used by Emma governance)
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    affected_files TEXT NOT NULL,
    risk TEXT,
    rollback_plan TEXT,
    estimated_impact TEXT,
    required_capabilities TEXT,
    timestamp TEXT NOT NULL,
    decision_context TEXT
);

-- Decisions table (approved/denied)
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (proposal_id) REFERENCES proposals(proposal_id)
);

-- Consent logging for simulated telephony
CREATE TABLE IF NOT EXISTS consent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    consent_flag BOOLEAN NOT NULL,
    description TEXT
);
