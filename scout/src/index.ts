import express, { Request, Response } from "express";
import client from "prom-client";

const SERVICE_NAME = "scout";
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

app.post(`/${SERVICE_NAME}/stub`, (req: Request, res: Response) => {
  httpRequestsTotal.inc({ method: "POST", route: `/${SERVICE_NAME}/stub`, status: 200 });
  res.json({ status: "ok", service: SERVICE_NAME, payload: req.body });
});

const port = Number(process.env.PORT) || 8102;
app.listen(port, () => {
  console.log(`${SERVICE_NAME} listening on port ${port}`);
});
