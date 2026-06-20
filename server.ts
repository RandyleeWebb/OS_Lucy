/**
 * LucyVerse OS — Production Server
 * Express + SQLite + Ollama/Claude fallback + Security Fabric
 * © 2026 Randy Webb (scottymicfree@gmail.com)
 */
import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import path from "path";
import { fileURLToPath } from "url";
import { randomUUID } from "crypto";
import { GoogleGenAI } from "@google/genai";
import Database from "better-sqlite3";
import fs from "fs";
import { actions as registryActions } from "./src/core/actions/registry.js";
import pino from "pino";
import SpotifyWebApi from "spotify-web-api-node";
import * as admin from "firebase-admin";
import { UniformManager } from "./src/core/personality/UniformManager.js";
import { EngineManager, EngineType } from "./src/core/execution/EngineManager.js";

const logger = pino({
  transport: {
    target: "pino-pretty",
    options: {
      colorize: true
    }
  }
});

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.PORT || "3002");
const OLLAMA_BASE = process.env.OLLAMA_BASE_URL || "http://localhost:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "llama3";
const EMMA_BASE = process.env.EMMA_URL || "http://localhost:8010";

// ── SQLite memory core ──────────────────────────────────────────────────
const db = new Database("lucyverse_memory.db");
db.pragma("journal_mode = WAL");
db.exec(`
  CREATE TABLE IF NOT EXISTS telemetry_events (
    id TEXT PRIMARY KEY, timestamp TEXT NOT NULL,
    type TEXT NOT NULL, sourceId TEXT NOT NULL, details TEXT
  );
  CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY, status TEXT NOT NULL,
    source_ip TEXT, fingerprint TEXT, created_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY, role TEXT NOT NULL, capabilities TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS datavault_entries (
    id TEXT PRIMARY KEY, source TEXT NOT NULL,
    payload TEXT NOT NULL, entry_hash TEXT, created_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS state_kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );
`);
// ── LanceDB vector memory ───────────────────────────────────────────────────
let vectorMemoryEnabled = false;
let lanceDb: any = null;
const LANCEDB_PATH = process.env.LANCEDB_PATH || path.join(__dirname, "lancedb-data");
try {
  // Ensure the directory exists and is writable
  fs.mkdirSync(LANCEDB_PATH, { recursive: true });
  const lancedb = await import('@lancedb/lancedb');
  logger.info(`[LanceDB] Using path: ${LANCEDB_PATH}`);
  lanceDb = await lancedb.connect(LANCEDB_PATH);
  vectorMemoryEnabled = true;
  logger.info("[LanceDB] Initialized successfully");
} catch (err: any) {
  logger.warn("[LanceDB] Initialization failed – proceeding without vector memory: " + err.message);
}
// Seed default agents
if ((db.prepare("SELECT COUNT(*) as c FROM agents").get() as any).c === 0) {
  const ins = db.prepare("INSERT INTO agents (id,role,capabilities) VALUES (?,?,?)");
  ins.run("lucy-core","Lucy",JSON.stringify(["Security.QueryStatus","Security.RequestDecision"]));
  ins.run("emma-gov","Emma",JSON.stringify(["Security.ApprovePolicyChanges","Security.EscalateSecurity","Security.Decide"]));
  ins.run("sentinel-sec","Sentinel",JSON.stringify(["Security.ReportEvents","Security.RequestContainment","Security.QueryStatus"]));
}

// ── Capability map ───────────────────────────────────────────────────────
const ROLE_CAPS: Record<string,string[]> = {
  Emma: ["Security.ApprovePolicyChanges","Security.EscalateSecurity","Security.Decide"],
  Sentinel: ["Security.ReportEvents","Security.RequestContainment","Security.QueryStatus"],
  Lucy: ["Security.QueryStatus","Security.RequestDecision"],
};
function verifyCap(role: string, cap: string) {
  return (ROLE_CAPS[role] || []).includes(cap);
}

// ── LLM helpers ──────────────────────────────────────────────────────────
const actionsText = registryActions.map(a => `- ${a.id}: ${a.label}`).join("\n");

async function chatOllama(messages: {role:string;text:string}[], systemPrompt: string) {
  const prompt = messages.map(m=>`${m.role==="user"?"USER":"LUCY"}: ${m.text}`).join("\n") + "\nLUCY:";
  const r = await fetch(`${OLLAMA_BASE}/api/generate`,{
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({model:OLLAMA_MODEL,prompt:`${systemPrompt}\n\n${prompt}`,stream:false}),
    signal: AbortSignal.timeout(120_000)
  });
  if (!r.ok) throw new Error(`Ollama ${r.status}`);
  return ((await r.json() as any).response || "").trim();
}

async function chatGemini(messages: {role:string;text:string}[], systemPrompt: string) {
  if (!process.env.GEMINI_API_KEY) throw new Error("No GEMINI_API_KEY");
  const ai = new GoogleGenAI({apiKey: process.env.GEMINI_API_KEY});
  const hist = messages.map(m=>`${m.role==="user"?"USER":"LUCY"}: ${m.text}`).join("\n");
  const r = await ai.models.generateContent({model:"gemini-2.5-flash",contents:`${systemPrompt}\n\n${hist}\n\nLUCY:`});
  return (r.text || "").trim();
}

async function chatClaude(messages: {role:string;text:string}[], systemPrompt: string) {
  if (!process.env.ANTHROPIC_API_KEY) throw new Error("No ANTHROPIC_API_KEY");
  const r = await fetch("https://api.anthropic.com/v1/messages",{
    method:"POST",
    headers:{"Content-Type":"application/json","x-api-key":process.env.ANTHROPIC_API_KEY,"anthropic-version":"2023-06-01"},
    body: JSON.stringify({
      model:"claude-sonnet-4-20250514", max_tokens:1000,
      system: systemPrompt,
      messages: messages.map(m=>({role:m.role==="user"?"user":"assistant",content:m.text}))
    }),
    signal: AbortSignal.timeout(30_000)
  });
  if (!r.ok) throw new Error(`Claude API ${r.status}`);
  const d = await r.json() as any;
  return (d.content?.[0]?.text || "").trim();
}

// ── Express ─────────────────────────────────────────────────────────────
const app = express();
app.use(express.json());

// Agent identity middleware
app.use((req: any, res: any, next: any) => {
  const role = (req.headers["x-agent-role"] as string) || "Lucy";
  const id = (req.headers["x-agent-id"] as string) || "default-lucy-node";
  (req as any).agentIdentity = {id, role, capabilities: ROLE_CAPS[role] || []};
  next();
});

const SAFEGUARD_URL = process.env.SAFEGUARD_URL || "http://localhost:8013";
const DATAVAULT_URL = process.env.DATAVAULT_URL || "http://localhost:8012";
const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || "http://localhost:8020";

// Proxy Emma terminal service
logger.info(`[Proxy] /terminal → ${EMMA_BASE}`);
app.use("/terminal", createProxyMiddleware({target:EMMA_BASE,changeOrigin:true,ws:true}));

logger.info(`[Proxy] /safeguard → ${SAFEGUARD_URL}`);
app.use("/safeguard", createProxyMiddleware({
  target: SAFEGUARD_URL,
  changeOrigin: true,
  pathRewrite: { "^/safeguard": "" }
}));

logger.info(`[Proxy] /datavault → ${DATAVAULT_URL}`);
app.use("/datavault", createProxyMiddleware({
  target: DATAVAULT_URL,
  changeOrigin: true,
  pathRewrite: { "^/datavault": "" }
}));

logger.info(`[Proxy] /orchestrator → ${ORCHESTRATOR_URL}`);
app.use("/orchestrator", createProxyMiddleware({
  target: ORCHESTRATOR_URL,
  changeOrigin: true,
  pathRewrite: { "^/orchestrator": "" }
}));

// ── State Management (Widgets, Tasks, Notes) ────────────────────────────
app.get("/api/state/:key", (req: any, res: any) => {
  const { key } = req.params;
  try {
    const row = db.prepare("SELECT value FROM state_kv WHERE key = ?").get(key) as any;
    if (row) {
      res.json({ success: true, data: JSON.parse(row.value) });
    } else {
      res.json({ success: true, data: null });
    }
  } catch (err: any) {
    logger.error('[State] GET ' + key + ' failed: ' + err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.post("/api/state/:key", (req: any, res: any) => {
  const { key } = req.params;
  const value = JSON.stringify(req.body);
  try {
    db.prepare(`
      INSERT INTO state_kv (key, value, updated_at) 
      VALUES (?, ?, ?) 
      ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    `).run(key, value, new Date().toISOString());
    res.json({ success: true });
  } catch (err: any) {
    logger.error('[State] POST ' + key + ' failed: ' + err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── Spotify Integration ──────────────────────────────────────────────────
const spotifyApi = new SpotifyWebApi({
  clientId: process.env.SPOTIFY_CLIENT_ID,
  clientSecret: process.env.SPOTIFY_CLIENT_SECRET,
  redirectUri: `http://localhost:${PORT}/api/spotify/callback`
});

app.get("/api/spotify/login", (req: any, res: any) => {
  if (!process.env.SPOTIFY_CLIENT_ID) {
    return res.status(500).json({ error: "SPOTIFY_CLIENT_ID not configured in .env" });
  }
  const scopes = ['user-read-playback-state', 'user-modify-playback-state', 'user-top-read'];
  const authorizeURL = spotifyApi.createAuthorizeURL(scopes, 'lucy-os-state');
  res.redirect(authorizeURL);
});

app.get("/api/spotify/callback", async (req: any, res: any) => {
  const code = req.query.code;
  try {
    const data = await spotifyApi.authorizationCodeGrant(code);
    spotifyApi.setAccessToken(data.body['access_token']);
    spotifyApi.setRefreshToken(data.body['refresh_token']);
    res.send("<script>window.close();</script>");
  } catch (err: any) {
    logger.error("[Spotify] Callback error: " + err.message);
    res.status(500).send("Spotify Authentication Failed");
  }
});

app.get("/api/spotify/now-playing", async (req: any, res: any) => {
  try {
    if (!spotifyApi.getAccessToken()) return res.json({ playing: false, error: "Not logged in" });
    const data = await spotifyApi.getMyCurrentPlaybackState();
    if (data.body && data.body.is_playing) {
      res.json({
        playing: true,
        item: data.body.item,
        progress_ms: data.body.progress_ms
      });
    } else {
      res.json({ playing: false });
    }
  } catch (err: any) {
    res.json({ playing: false, error: err.message });
  }
});

app.get("/api/spotify/top-tracks", async (req: any, res: any) => {
  try {
    if (!spotifyApi.getAccessToken()) return res.json({ error: "Not logged in" });
    const data = await spotifyApi.getMyTopTracks({ limit: 5 });
    res.json(data.body.items);
  } catch (err: any) {
    res.json({ error: err.message });
  }
});

// ── Firebase Push Notifications ─────────────────────────────────────────
let firebaseEnabled = false;
let firebaseMessaging: any = null;
if (process.env.FIREBASE_SERVICE_ACCOUNT) {
  try {
    const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
    admin.initializeApp({ credential: (admin as any).credential.cert(serviceAccount) });
    firebaseMessaging = (admin as any).messaging();
    firebaseEnabled = true;
    logger.info("[Firebase] Admin initialized successfully");
  } catch (err: any) {
    logger.error(`[Firebase] Init error: ${err.message}`);
  }
} else {
  logger.info("[Firebase] Disabled (no service account provided)");
}
app.post("/api/device/register", async (req: any, res: any) => {
  const { token, deviceId } = req.body;
  if (!token) return res.status(400).json({ error: "No token provided" });
  
  try {
    // Store the FCM token in SQLite
    db.prepare(`
      INSERT INTO state_kv (key, value, updated_at) 
      VALUES (?, ?, ?) 
      ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    `).run(`fcm_token_${deviceId || 'default'}`, JSON.stringify({ token }), new Date().toISOString());
    
    res.json({ success: true, message: "Device registered" });
  } catch (err: any) {
    logger.error(`[Firebase] Registration error: ${err.message}`);
    res.status(500).json({ error: err.message });
  }
});

app.post("/api/device/notify", async (req: any, res: any) => {
  const { title, body, deviceId } = req.body;
  try {
    const row = db.prepare("SELECT value FROM state_kv WHERE key = ?").get(`fcm_token_${deviceId || 'default'}`) as any;
    if (!row) return res.status(404).json({ error: "Device not registered" });
    
    const { token } = JSON.parse(row.value);
    const message = {
      notification: { title, body },
      token
    };
    
if (!firebaseEnabled) {
    logger.warn('[Firebase] Notification endpoint called but Firebase is disabled');
    return res.status(503).json({ error: 'Firebase disabled' });
  }
  const response = await firebaseMessaging.send(message);
  } catch (err: any) {
    logger.error(`[Firebase] Send notification error: ${err.message}`);
    res.status(500).json({ error: err.message });
  }
});

// ── Chat (Ollama → Claude → Gemini fallback chain) ──────────────────────
app.post("/api/chat", async (req: any, res: any) => {
  const {messages, contextState} = req.body;
  const lastMessage = messages[messages.length - 1]?.text || "";
  
  // 1. Heuristic Classifier
  let heuristicResult = EngineManager.heuristicClassify(lastMessage, contextState);
  let activeEngine = heuristicResult.engineType;
  
  // Fallback to LLM if low confidence
  if (heuristicResult.confidence < 0.7) {
    try {
      const llmPrompt = `Classify this prompt into one of these engines: LUCY_CHAT, LUCY_RESEARCH, EMMA_TASK, EMMA_SYSTEM.
      Prompt: "${lastMessage}"
      Only output the EXACT engine name. Nothing else.`;
      const fallbackEngineStr = await chatGemini([{role:"user", text:llmPrompt}], "You are a classifier.");
      if (Object.values(EngineType).includes(fallbackEngineStr as any)) {
        activeEngine = fallbackEngineStr as EngineType;
        logger.info(`[EMS] LLM Fallback routed to ${activeEngine}`);
      }
    } catch(e) {
      logger.warn('[EMS] LLM classifier fallback failed, using default');
      activeEngine = EngineType.LUCY_CHAT;
    }
  } else {
    logger.info(`[EMS] Heuristic routed to ${activeEngine} (conf: ${heuristicResult.confidence})`);
  }
  
  let engineConfig = EngineManager.getEngineConfig(activeEngine, actionsText);
  let activePipeline = engineConfig.agent === 'Lucy' ? 'LUCY' : 'EMMA';
  
  for (const [fn, name] of [[chatOllama,"ollama"],[chatClaude,"claude"],[chatGemini,"gemini"]] as any) {
    try {
      if (activePipeline === 'LUCY') {
        const outfit = UniformManager.getUniformModifier(lastMessage, contextState);
        const lucyPrompt = `${engineConfig.systemPrompt}\n\n${outfit}`;
        const text = await fn(messages, lucyPrompt);
        
        // Handoff check
        if (text.includes('[HANDOFF: Emma]')) {
          logger.info('[Chat] Lucy initiated handoff to Emma');
          activePipeline = 'EMMA';
          activeEngine = EngineType.EMMA_TASK;
          engineConfig = EngineManager.getEngineConfig(activeEngine, actionsText);
          // Fall through to execute Emma pipeline
        } else {
          return res.json({text, backend:name, pipeline:`${activeEngine}`});
        }
      }
      
      if (activePipeline === 'EMMA') {
        const text = await fn(messages, engineConfig.systemPrompt);
        return res.json({text, backend:name, pipeline:`${activeEngine}`});
      }
    } catch(e:any) {
      logger.warn(`[Chat] ${name} failed: ${e.message}`);
    }
  }
  return res.status(503).json({text:"⚠ All LLM backends offline. Check Ollama or set ANTHROPIC_API_KEY / GEMINI_API_KEY.", backend:"none"});
});

// ── Status ───────────────────────────────────────────────────────────────
app.get("/api/status", async (_req: any, res: any) => {
  let ollamaOk=false;
  try {const r=await fetch(`${OLLAMA_BASE}/api/tags`,{signal:AbortSignal.timeout(2000)});ollamaOk=r.ok}catch{}
  const totalLogs=(db.prepare("SELECT COUNT(*) as c FROM telemetry_events").get() as any).c;
  res.json({lucyverse:"ONLINE",chat:ollamaOk?"ollama":process.env.ANTHROPIC_API_KEY?"claude":process.env.GEMINI_API_KEY?"gemini":"OFFLINE",ollama:ollamaOk?"UP":"DOWN",ollamaModel:OLLAMA_MODEL,claude:!!process.env.ANTHROPIC_API_KEY?"configured":"no key",gemini:!!process.env.GEMINI_API_KEY?"configured":"no key",telemetryEvents:totalLogs});
});

// ── Sovereign AI OS Read-Only Endpoints ─────────────────────────────────
let lucyCoreDb: any = null;
try {
  const dbPath = path.join(__dirname, "data", "lucy.db");
  if (fs.existsSync(dbPath)) {
    lucyCoreDb = new Database(dbPath, { readonly: true });
  }
} catch (e: any) {
  logger.warn(`Could not open lucy.db: ${e.message}`);
}

app.get("/health", (req: any, res: any) => {
  res.json({ status: "ok", os: "Sovereign AI OS" });
});

app.get("/event", (req: any, res: any) => {
  try {
    const events = db.prepare("SELECT * FROM telemetry_events ORDER BY timestamp DESC LIMIT 50").all();
    res.json(events);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.get("/incidents", (req: any, res: any) => {
  if (!lucyCoreDb) return res.json([]);
  try {
    const incidents = lucyCoreDb.prepare("SELECT * FROM incident_memory ORDER BY timestamp DESC LIMIT 50").all();
    res.json(incidents);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.get("/security", (req: any, res: any) => {
  if (!lucyCoreDb) return res.json([]);
  try {
    const alerts = lucyCoreDb.prepare("SELECT * FROM security_memory ORDER BY timestamp DESC LIMIT 50").all();
    res.json(alerts);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.get("/boot_status", (req: any, res: any) => {
  try {
    const p = path.join(__dirname, "luclog_resource", "boot_incidents.json");
    if (fs.existsSync(p)) {
      const data = fs.readFileSync(p, "utf-8");
      res.json(JSON.parse(data));
    } else {
      res.json([]);
    }
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.get("/persona", (req: any, res: any) => {
  try {
    const p = path.join(__dirname, "src", "memory", "persona.txt");
    if (fs.existsSync(p)) {
      res.send(fs.readFileSync(p, "utf-8"));
    } else {
      res.send("Persona block not found.");
    }
  } catch (e: any) {
    res.status(500).send(e.message);
  }
});

app.get("/diagnostics", async (req: any, res: any) => {
  try {
    const r = await fetch("http://localhost:5000/diagnostics");
    if (!r.ok) throw new Error("Python proxy failed");
    const data = await r.json();
    res.json(data);
  } catch(e:any) {
    res.status(500).json({ error: e.message });
  }
});


// ── Security Fabric ───────────────────────────────────────────────────────
app.post("/api/security/decide", (req: any, res: any) => {
  const identity = (req as any).agentIdentity;
  if (!verifyCap(identity.role,"Security.RequestDecision")) return res.status(403).json({verdict:"deny",reason:"Unauthorized"});
  const {action, targetId, payloadFingerprint} = req.body;
  let verdict = "allow";
  if (action==="EXECUTE_UNTRUSTED"||action==="SYNTHETIC_QUARANTINE_THREAT") verdict="quarantine";
  else if (action==="SYNTHETIC_MAZE_THREAT"||payloadFingerprint==="malicious_signature") verdict="maze";
  const actionId = randomUUID();
  if (verdict!=="allow") {
    db.prepare("INSERT INTO sessions (id,status,source_ip,fingerprint,created_at) VALUES (?,?,?,?,?)").run(actionId,verdict,"192.168.x.x",payloadFingerprint||"synthetic",new Date().toISOString());
    db.prepare("INSERT INTO telemetry_events (id,timestamp,type,sourceId,details) VALUES (?,?,?,?,?)").run(randomUUID(),new Date().toISOString(),verdict==="quarantine"?"PANDORA_VM_SPAWNED":"INFINITE_MAZE_ENGAGED","emma-gov",JSON.stringify({reason:action,targetId,payloadFingerprint}));
    triggerDeception(actionId,verdict).catch(err => logger.error(`Deception Error: ${err.message}`));
  }
  res.json({verdict,actionId,message:verdict==="quarantine"?"Routing to Pandora microVM":verdict==="maze"?"Routing to Infinite Maze":"Allowed"});
});

app.post("/api/security/report", (req: any, res: any) => {
  const identity = (req as any).agentIdentity;
  if (!verifyCap(identity.role,"Security.ReportEvents")) return res.status(403).json({error:"Unauthorized"});
  const {type,details} = req.body;
  const eventId = randomUUID();
  db.prepare("INSERT INTO telemetry_events (id,timestamp,type,sourceId,details) VALUES (?,?,?,?,?)").run(eventId,new Date().toISOString(),type,identity.id,JSON.stringify(details));
  res.json({success:true,eventId});
});

app.get("/api/security/status", (req: any, res: any) => {
  const identity = (req as any).agentIdentity;
  if (!verifyCap(identity.role,"Security.QueryStatus")) return res.status(403).json({error:"Unauthorized"});
  const totalLogs=(db.prepare("SELECT COUNT(*) as c FROM telemetry_events").get() as any).c;
  const recentEvents=db.prepare("SELECT * FROM telemetry_events ORDER BY timestamp DESC LIMIT 10").all();
  const quarantinedCount=(db.prepare("SELECT COUNT(*) as c FROM sessions WHERE status=?").get("quarantine") as any).c;
  const mazeCount=(db.prepare("SELECT COUNT(*) as c FROM sessions WHERE status=?").get("maze") as any).c;
  res.json({activeAlerts:totalLogs,recentEvents,quarantinedVMs:quarantinedCount,tarpittedConnections:mazeCount,fabricStatus:"ONLINE"});
});

app.get("/api/security/events", (_req: any, res: any) => {
  res.json(db.prepare("SELECT * FROM telemetry_events ORDER BY timestamp ASC LIMIT 100").all());
});

// Mock handlers removed. Proxy middleware redirects all /safeguard, /datavault, and /orchestrator routes to the real microservices.

// ── Generative Deception Engine ───────────────────────────────────────────
async function triggerDeception(sessionId: string, verdict: string) {
  const key = process.env.GEMINI_API_KEY || process.env.ANTHROPIC_API_KEY;
  if (!key) {
    db.prepare("INSERT INTO telemetry_events (id,timestamp,type,sourceId,details) VALUES (?,?,?,?,?)").run(randomUUID(),new Date().toISOString(),"SYSTEM_WARNING","fabric-gde",JSON.stringify({message:"No AI key — Generative Deception offline"}));
    return;
  }
  try {
    const prompt = verdict==="maze"
      ? "Generate 3 realistic synthetic nginx access log lines from an aggressive vulnerability scanner. ONLY raw text."
      : "Generate 3 realistic bash history commands a malicious actor would run after compromising a Linux container. ONLY raw text.";
    let payload = "";
    if (process.env.GEMINI_API_KEY) {
      const ai = new GoogleGenAI({apiKey:process.env.GEMINI_API_KEY});
      const r = await ai.models.generateContent({model:"gemini-2.5-flash",contents:prompt});
      payload = (r.text||"").replace(/```[a-z]*/g,"").replace(/```/g,"").trim();
    }
    db.prepare("INSERT INTO telemetry_events (id,timestamp,type,sourceId,details) VALUES (?,?,?,?,?)").run(randomUUID(),new Date().toISOString(),"GENERATIVE_DECEPTION_ACTIVE","gemini-gde",JSON.stringify({sessionId,payload}));
  } catch(e:any) {
    db.prepare("INSERT INTO telemetry_events (id,timestamp,type,sourceId,details) VALUES (?,?,?,?,?)").run(randomUUID(),new Date().toISOString(),"SYSTEM_ERROR","gemini-gde",JSON.stringify({error:e.message}));
  }
}

// ── Static / Dev ──────────────────────────────────────────────────────────
if (process.env.NODE_ENV === "production") {
  const dist = path.join(__dirname, "dist");
  app.use(express.static(dist));
  app.get("*", (_req: any, res: any) => res.sendFile(path.join(dist,"index.html")));
} else {
  const {createServer} = await import("vite");
  const vite = await createServer({server:{middlewareMode:true},appType:"spa"});
  app.use(vite.middlewares);
}

app.listen(PORT, "0.0.0.0", () => {
  logger.info(`\n╔══════════════════════════════════════════════╗
║        LucyVerse OS — Production Server      ║
╚══════════════════════════════════════════════╝
  URL:      http://localhost:${PORT}
  Ollama:   ${OLLAMA_BASE} (${OLLAMA_MODEL})
  Claude:   ${process.env.ANTHROPIC_API_KEY?"✓ configured":"✗ no key"}
  Gemini:   ${process.env.GEMINI_API_KEY?"✓ configured":"✗ no key"}\n`);
});
