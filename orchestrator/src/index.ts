import express, { Request, Response } from "express";
import client from "prom-client";
import { v4 as uuidv4 } from "uuid";

const SERVICE_NAME = "orchestrator";
const app = express();
app.use(express.json());

// Prometheus metrics
const register = new client.Registry();
client.collectDefaultMetrics({ register });

const httpRequestsTotal = new client.Counter({
  name: `${SERVICE_NAME}_http_requests_total`,
  help: "Total HTTP requests",
  labelNames: ["method", "route", "status"]
});
register.registerMetric(httpRequestsTotal);

app.get("/health", (_req: Request, res: Response) => {
  httpRequestsTotal.inc({ method: "GET", route: "/health", status: 200 });
  res.json({ up: true, service: SERVICE_NAME, version: "0.1.0" });
});

app.get("/metrics", async (_req: Request, res: Response) => {
  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
});

interface IntentPayload {
  intent_id?: string;
  action: string;
  parameters: Record<string, any>;
  timestamp?: string;
  metadata?: Record<string, any>;
}

app.post("/orchestrator/route", async (req: Request, res: Response) => {
  httpRequestsTotal.inc({ method: "POST", route: "/orchestrator/route", status: 200 });
  
  try {
    const rawIntent: Partial<IntentPayload> = req.body || {};
    if (!rawIntent.action) {
      throw new Error("Missing required field: action");
    }

    const intent = {
      intent_id: rawIntent.intent_id || uuidv4(),
      action: rawIntent.action,
      parameters: rawIntent.parameters || {},
      timestamp: rawIntent.timestamp || new Date().toISOString(),
      metadata: rawIntent.metadata || {}
    };

    // 1. Call SafeGuard
    const sgRes = await fetch("http://policy_engine:8500/safeguard/eval", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(intent)
    });
    if (!sgRes.ok) throw new Error(`SafeGuard request failed with status: ${sgRes.status}`);
    const sgData = await sgRes.json();
    if (!sgData.permitted) {
      throw new Error(`Execution blocked by SafeGuard: ${sgData.reasons.join(", ")}`);
    }

    // 2. Pre-log DataVault
    const preLogRes = await fetch("http://vault_api:8604/vault/append", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        intent_id: intent.intent_id,
        timestamp: intent.timestamp,
        actor: "orchestrator",
        intent_hash: "TODO:hash", // Would compute hash of intent
        safeguard_decision: JSON.stringify(sgData),
        execution_metrics: "PENDING",
        signature: "unsigned"
      })
    });
    if (!preLogRes.ok) throw new Error(`DataVault pre-log failed with status: ${preLogRes.status}`);

    // 3. Execute Trusted Executor
    const execRes = await fetch("http://executor_api:8403/executor/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(intent)
    });
    if (!execRes.ok) throw new Error(`Trusted Executor failed with status: ${execRes.status}`);
    const execData = await execRes.json();

    // 4. Post-log DataVault
    const postLogRes = await fetch("http://vault_api:8604/vault/append", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        intent_id: intent.intent_id,
        timestamp: new Date().toISOString(),
        actor: "executor",
        intent_hash: "TODO:hash",
        safeguard_decision: JSON.stringify(sgData),
        execution_metrics: JSON.stringify({ fuel_used: execData.fuel_used, memory_pages: execData.memory_pages }),
        signature: "unsigned"
      })
    });
    if (!postLogRes.ok) throw new Error(`DataVault post-log failed with status: ${postLogRes.status}`);

    res.json(execData);
  } catch (err: any) {
    console.error("Pipeline failure:", err.message);
    res.status(500).json({ error: err.message || "Pipeline failed" });
  }
});

const port = Number(process.env.PORT) || 8000;
app.listen(port, () => {
  console.log(`${SERVICE_NAME} listening on port ${port}`);
});
