from fastapi import FastAPI
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import asyncio
import httpx
import logging
import sys

# Configure stdout logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] GovernanceDaemon: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("governance_daemon")

SERVICE_NAME = "governance_daemon"
VERIFIER_URL = "http://hash_chain_verifier:8901"

app = FastAPI(title=f"Lucy {SERVICE_NAME}")

http_requests_total = Counter(
    f"{SERVICE_NAME}_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"]
)

verification_errors = Counter(
    f"{SERVICE_NAME}_verification_errors_total",
    "Total times the ledger verification failed"
)

async def audit_loop():
    logger.info("Starting governance audit loop...")
    while True:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(f"{VERIFIER_URL}/verify", timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        logger.info(f"Ledger verified successfully. Entries: {data.get('verified_entries')}")
                    else:
                        logger.error(f"LEDGER CORRUPTION DETECTED: {data.get('error')}")
                        verification_errors.inc()
                else:
                    logger.warning(f"Verifier returned non-200 status: {res.status_code}")
        except Exception as e:
            logger.warning(f"Failed to contact verifier: {e}")
            
        await asyncio.sleep(15) # Audit every 15 seconds

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(audit_loop())

@app.get("/health")
async def health():
    http_requests_total.labels("GET", "/health", 200).inc()
    return {"up": True, "service": SERVICE_NAME, "version": "0.1.0"}

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
