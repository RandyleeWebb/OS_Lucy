# Lucy's Docker Setup & Debugging Guide

## Current Issues Found

1. **Missing Dockerfiles**: Services in `Code/*/` directories don't have Dockerfiles
2. **Mixed old/new compose**: Old container names conflict with new compose config
3. **Dependency chain**: New compose requires all custom services built first

---

## Phase 1: Clean Up Old Containers

```bash
# Remove old orphaned containers
docker compose down --remove-orphans

# Or force-remove everything
docker system prune -a --volumes
```

---

## Phase 2: Create Dockerfiles for Each Service

Each service in `Code/*/` needs a Dockerfile. Use this template:

### For Python/FastAPI Services:

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
COPY . .
EXPOSE ${PORT:-8000}
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]
```

### For Node.js Services:

```dockerfile
FROM node:20-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
EXPOSE ${PORT:-8000}
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=10s \
  CMD wget -qO- http://localhost:${PORT:-8000}/health || exit 1
CMD ["npm", "start"]
```

**Required files per service:**
- `Dockerfile` - dockerfile in the service directory
- `requirements.txt` (Python) or `package.json` (Node.js)
- `main.py` or `main:app` (FastAPI entry point)

---

## Phase 3: Build All Services

```bash
# Build all images at once
docker compose build --no-cache

# Or build specific services
docker compose build policy_engine
docker compose build orchestrator
```

---

## Phase 4: Start Infrastructure Only (Recommended First)

```bash
# Start just the infrastructure layer (no custom services)
docker compose -f docker-compose.infrastructure.yml up -d

# Wait 30 seconds for services to stabilize
sleep 30

# Check status
docker compose -f docker-compose.infrastructure.yml ps
```

Expected output:
```
NAME         STATUS
redis        Up (healthy)
postgres     Up (healthy)
minio        Up (healthy)
qdrant       Up (healthy)
nats         Up (healthy)
prometheus   Up (healthy)
grafana      Up (healthy)
ollama       Up (healthy)
```

---

## Phase 5: Start Full Stack (After Dockerfiles Created)

```bash
# Start everything with proper layered startup
docker compose up -d

# Monitor startup progress
watch 'docker compose ps'

# Or check specific service logs
docker compose logs orchestrator -f
```

---

## Troubleshooting

### Container exits immediately
```bash
docker logs <container_name>
# Look for missing dependencies, Python/Node errors, port conflicts
```

### Health check fails
```bash
# Test manually
docker exec <container_name> curl http://localhost:8000/health
```

### Port already in use
```bash
# Find what's using port 8000
netstat -an | grep 8000
lsof -i :8000  # macOS/Linux
```

### Memory issues
```bash
docker stats
# If high memory, reduce Grafana startup time in healthcheck
```

### Compose file invalid
```bash
docker compose config
# Shows syntax errors in docker-compose.yml
```

---

## Service Port Map

| Service | Port | Type |
|---------|------|------|
| Redis | 6379 | Cache/Queue |
| Postgres | 5432 | Database |
| MinIO | 9000 | Object Storage |
| Qdrant | 6333 | Vector DB |
| NATS | 4222 | Message Bus |
| Prometheus | 9090 | Metrics |
| Grafana | 3000 | UI/Dashboards |
| Ollama | 11434 | LLM |
| Orchestrator | 8000 | Main API |
| Chat | 9001 | Chat API |

---

## Required Environment Variables

Create or update `.env`:
```
POSTGRES_PASSWORD=postgres
REDIS_PASSWORD=
QDRANT_API_KEY=
NATS_USER=
PORT=8000
```

---

## Quick Health Check Script

```bash
#!/bin/bash
for service in redis postgres minio qdrant nats prometheus grafana ollama; do
  state=$(docker ps -q -f "name=$service")
  [ -n "$state" ] && echo "✅ $service" || echo "❌ $service"
done
```

---

## Next Steps

1. **Create all Dockerfiles** (see Phase 2)
2. **Build images** (see Phase 3)
3. **Start infrastructure first** (see Phase 4)
4. **Verify health** (check ports above)
5. **Scale to full stack** (see Phase 5)

If any custom service fails to start, check:
- Does `Code/<service>/Dockerfile` exist?
- Does `Code/<service>/requirements.txt` or `package.json` exist?
- Does the service have a health check endpoint at `/<PORT>/health`?
