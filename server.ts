import express from "express";
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from "path";
import { createServer as createViteServer } from "vite";
import {
  AgentIdentity,
  Capability,
  SecurityActionType,
  SecurityEvent,
} from "./src/types/system.js";
import { randomUUID } from "crypto";
import { GoogleGenAI } from "@google/genai";
import Database from "better-sqlite3";

// --- SHARED MEMORY CORE (SQLite) ---
const db = new Database("lucyverse_memory.db");
db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS telemetry_events (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    sourceId TEXT NOT NULL,
    details TEXT
  );

  CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    source_ip TEXT,
    fingerprint TEXT,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    capabilities TEXT NOT NULL
  );
`);

const countObj = db.prepare("SELECT COUNT(*) as count FROM agents").get() as { count: number };
if (countObj.count === 0) {
  const insertAgent = db.prepare("INSERT INTO agents (id, role, capabilities) VALUES (?, ?, ?)");
  insertAgent.run("lucy-core", "Lucy", JSON.stringify(["Security.QueryStatus", "Security.RequestDecision"]));
  insertAgent.run("emma-gov", "Emma", JSON.stringify(["Security.ApprovePolicyChanges", "Security.EscalateSecurity", "Security.Decide"]));
  insertAgent.run("sentinel-sec", "Sentinel", JSON.stringify(["Security.ReportEvents", "Security.RequestContainment", "Security.QueryStatus"]));
}

// --- CAPABILITY MANAGER ---
const ROLE_CAPABILITIES: Record<string, Capability[]> = {
  Emma: ["Security.ApprovePolicyChanges", "Security.EscalateSecurity", "Security.Decide" as any],
  Sentinel: ["Security.ReportEvents", "Security.RequestContainment", "Security.QueryStatus"],
  Lucy: ["Security.QueryStatus", "Security.RequestDecision"],
};

function verifyCapability(identity: AgentIdentity, requiredCap: Capability): boolean {
  const roleCaps = ROLE_CAPABILITIES[identity.role] || [];
  return roleCaps.includes(requiredCap) || identity.capabilities.includes(requiredCap);
}

// --- OLLAMA CONFIG ---
const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || "http://localhost:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "llama3";

async function chatWithOllama(messages: { role: string; text: string }[]): Promise<string> {
  const prompt = messages.map(m => `${m.role === "user" ? "USER" : "LUCY"}: ${m.text}`).join("\n") + "\nLUCY:";
  const response = await fetch(`${OLLAMA_BASE_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: OLLAMA_MODEL,
      prompt: `You are Lucy Core, a systems-level AI engineering orchestrator inside a modular cognitive runtime. Respond concisely and in an engineering-focused manner. Do not use quotes or prefixes — just your direct response.\n\n${prompt}`,
      stream: false,
    }),
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw new Error(`Ollama ${response.status}`);
  const data = await response.json() as any;
  return (data.response || "").trim();
}

async function chatWithGemini(messages: { role: string; text: string }[]): Promise<string> {
  if (!process.env.GEMINI_API_KEY) throw new Error("GEMINI_API_KEY not set");
  const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
  const formattedHistory = messages.map(m => `${m.role === "user" ? "USER" : "LUCY"}: ${m.text}`).join("\n");
  const prompt = `You are Lucy Core, a systems-level AI engineering orchestrator operating inside a modular cognitive runtime. Respond concisely and in an engineering-focused manner. Do not use quotes or prefixes — just your direct response.\n\nConversation History:\n${formattedHistory}\n\nLUCY:`;
  const response = await ai.models.generateContent({ model: "gemini-2.5-flash", contents: prompt });
  return (response.text || "").trim();
}

// --- EXPRESS APP ---
const app = express();
app.use(express.json());
const PORT = parseInt(process.env.PORT || "3000");

app.use((req, res, next) => {
  const role = (req.headers["x-agent-role"] as any) || "Lucy";
  const agentId = (req.headers["x-agent-id"] as string) || "default-lucy-node";
  (req as any).agentIdentity = { id: agentId, role, capabilities: ROLE_CAPABILITIES[role] || [] };
  next();
});

// --- LOCAL PROXY: forward /terminal HTTP and WebSocket traffic to Emma service ---
const EMMA_BASE = process.env.EMMA_URL || "http://localhost:8010";
console.log(`[Proxy] forwarding /terminal -> ${EMMA_BASE}`);
app.use('/terminal', createProxyMiddleware({ target: EMMA_BASE, changeOrigin: true, ws: true, logLevel: 'warn' }));

// --- CHAT ENDPOINT (Ollama-first, Gemini fallback) ---
app.post("/api/chat", async (req, res) => {
  const { messages } = req.body;

  // 1. Try Ollama first
  try {
    const text = await chatWithOllama(messages);
    console.log("[Chat] Responded via Ollama");
    return res.json({ text, backend: "ollama" });
  } catch (ollamaErr: any) {
    console.warn(`[Chat] Ollama unavailable (${ollamaErr.message}), falling back to Gemini...`);
  }

  // 2. Fallback to Gemini
  try {
    const text = await chatWithGemini(messages);
    console.log("[Chat] Responded via Gemini");
    return res.json({ text, backend: "gemini" });
  } catch (geminiErr: any) {
    console.error("[Chat] Both backends failed:", geminiErr.message);
    return res.status(503).json({
      text: "⚠ Lucy offline — both Ollama and Gemini unavailable. Check Ollama is running or set GEMINI_API_KEY.",
      backend: "none",
    });
  }
});

// --- HEALTH + BACKEND STATUS ---
app.get("/api/status", async (req, res) => {
  let ollamaOk = false;
  try {
    const r = await fetch(`${OLLAMA_BASE_URL}/api/tags`, { signal: AbortSignal.timeout(3000) });
    ollamaOk = r.ok;
  } catch {}

  const geminiOk = !!process.env.GEMINI_API_KEY;
  const totalLogs = (db.prepare("SELECT COUNT(*) as c FROM telemetry_events").get() as any).c;

  res.json({
    lucyverse: "ONLINE",
    chat: ollamaOk ? "ollama" : geminiOk ? "gemini" : "OFFLINE",
    ollama: ollamaOk ? "UP" : "DOWN",
    ollamaModel: OLLAMA_MODEL,
    gemini: geminiOk ? "configured" : "no key",
    telemetryEvents: totalLogs,
  });
});

// --- SECURITY FABRIC (unchanged from original) ---
app.post("/api/security/decide", (req, res) => {
  const identity = (req as any).agentIdentity as AgentIdentity;
  if (!verifyCapability(identity, "Security.RequestDecision")) {
    return res.status(403).json({ verdict: "deny", reason: "Unauthorized: Lacking Security.RequestDecision capability" });
  }
  const { action, targetId, payloadFingerprint } = req.body;
  console.log(`[Agent Bus] -> Emma observing Decision Request from ${identity.role}`);
  let verdict = "allow";
  if (action === "EXECUTE_UNTRUSTED" || action === "SYNTHETIC_QUARANTINE_THREAT") verdict = "quarantine";
  else if ((action === "NETWORK_INBOUND" && payloadFingerprint === "malicious_signature") || action === "SYNTHETIC_MAZE_THREAT") verdict = "maze";
  const actionId = randomUUID();
  if (verdict === "quarantine" || verdict === "maze") {
    db.prepare("INSERT INTO sessions (id, status, source_ip, fingerprint, created_at) VALUES (?, ?, ?, ?, ?)").run(actionId, verdict, "192.168.x.x", payloadFingerprint || "synthetic", new Date().toISOString());
    db.prepare("INSERT INTO telemetry_events (id, timestamp, type, sourceId, details) VALUES (?, ?, ?, ?, ?)").run(randomUUID(), new Date().toISOString(), verdict === "quarantine" ? "PANDORA_VM_SPAWNED" : "INFINITE_MAZE_ENGAGED", "emma-gov", JSON.stringify({ reason: action, targetId, payloadFingerprint }));
    triggerDeceptionEngine(actionId, verdict).catch(console.error);
  }
  res.json({ verdict, actionId, message: verdict === "quarantine" ? "Routing to Pandora microVM" : verdict === "maze" ? "Routing to Infinite Maze" : "Allowed" });
});

app.post("/api/security/report", (req, res) => {
  const identity = (req as any).agentIdentity as AgentIdentity;
  if (!verifyCapability(identity, "Security.ReportEvents")) return res.status(403).json({ error: "Unauthorized: Lacking Security.ReportEvents capability" });
  const { type, details } = req.body;
  const eventId = randomUUID();
  db.prepare("INSERT INTO telemetry_events (id, timestamp, type, sourceId, details) VALUES (?, ?, ?, ?, ?)").run(eventId, new Date().toISOString(), type, identity.id, JSON.stringify(details));
  console.log(`[Security Fabric] Ingested event from ${identity.role}: ${type}`);
  res.json({ success: true, eventId });
});

app.get("/api/security/status", (req, res) => {
  const identity = (req as any).agentIdentity as AgentIdentity;
  if (!verifyCapability(identity, "Security.QueryStatus")) return res.status(403).json({ error: "Unauthorized" });
  const totalLogs = (db.prepare("SELECT COUNT(*) as c FROM telemetry_events").get() as any).c;
  const recentEvents = db.prepare("SELECT * FROM telemetry_events ORDER BY timestamp DESC LIMIT 10").all() || [];
  const quarantinedCount = (db.prepare("SELECT COUNT(*) as c FROM sessions WHERE status = ?").get("quarantine") as any).c;
  const mazeCount = (db.prepare("SELECT COUNT(*) as c FROM sessions WHERE status = ?").get("maze") as any).c;
  res.json({ activeAlerts: totalLogs, recentEvents: recentEvents.reverse(), quarantinedVMs: quarantinedCount, tarpittedConnections: mazeCount, fabricStatus: "ONLINE", message: "Aegis-Pandora Fabric Operational." });
});

app.get("/api/security/events", (req, res) => {
  res.json(db.prepare("SELECT * FROM telemetry_events ORDER BY timestamp ASC LIMIT 100").all());
});

async function triggerDeceptionEngine(sessionId: string, verdict: string) {
  if (!process.env.GEMINI_API_KEY) {
    db.prepare("INSERT INTO telemetry_events (id, timestamp, type, sourceId, details) VALUES (?, ?, ?, ?, ?)").run(randomUUID(), new Date().toISOString(), "SYSTEM_WARNING", "fabric-gde", JSON.stringify({ message: "GEMINI_API_KEY missing. Generative Deception Offline." }));
    return;
  }
  try {
    const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
    const prompt = verdict === "maze"
      ? "Generate exactly 3 lines of highly realistic, synthetic Linux nginx access log entries reflecting an aggressive vulnerability scanner hitting a honeypot. Output ONLY raw text, no markdown."
      : "Generate exactly 3 highly realistic bash history commands that a malicious actor might run upon compromising a Linux container. Output ONLY raw text, no markdown.";
    const response = await ai.models.generateContent({ model: "gemini-2.5-flash", contents: prompt });
    const payload = (response.text || "").replace(/```(bash|text|log)?/g, "").replace(/```/g, "").trim();
    db.prepare("INSERT INTO telemetry_events (id, timestamp, type, sourceId, details) VALUES (?, ?, ?, ?, ?)").run(randomUUID(), new Date().toISOString(), "GENERATIVE_DECEPTION_ACTIVE", "gemini-gde", JSON.stringify({ sessionId, payload }));
  } catch (err: any) {
    db.prepare("INSERT INTO telemetry_events (id, timestamp, type, sourceId, details) VALUES (?, ?, ?, ?, ?)").run(randomUUID(), new Date().toISOString(), "SYSTEM_ERROR", "gemini-gde", JSON.stringify({ error: err.message }));
  }
}

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({ server: { middlewareMode: true }, appType: "spa" });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => res.sendFile(path.join(distPath, "index.html")));
  }
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[LucyVerse] Server on http://localhost:${PORT}`);
    console.log(`[LucyVerse] Ollama: ${OLLAMA_BASE_URL} (model: ${OLLAMA_MODEL})`);
    console.log(`[LucyVerse] Gemini: ${process.env.GEMINI_API_KEY ? "configured" : "no key - ollama only"}`);
  });
}

startServer();
