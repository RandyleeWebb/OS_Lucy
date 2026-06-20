# Lucy Docker Quick Reference

## 🚀 Quick Start

**Option 1: Infrastructure Only (Safe - Works Now)**
```bash
docker compose -f docker-compose.infrastructure.yml up -d
```

**Option 2: Full Stack (Requires Dockerfiles)**
```bash
docker compose up -d
```

**Option 3: Phased Startup**
```bash
start_lucy_fixed.bat
```

---

## 📊 Current Status

### Infrastructure (Running)
✅ Redis (6379)       - Cache  
✅ Postgres (5432)    - Database  
✅ MinIO (9000)       - Object Storage  
✅ NATS (4222)        - Message Bus  
✅ Prometheus (9090)  - Metrics  
⚠️  Qdrant (6333)     - Vector DB (unhealthy = still initializing)  
⚠️  Grafana (3000)    - Dashboard (unhealthy = doing migrations)  
⚠️  Ollama (11434)    - LLM (starting)  

**Note:** "Unhealthy" means health check is failing, but services are operational. They'll become "healthy" in 2-5 minutes.

---

## 🔧 Common Commands

### Check Status
```bash
docker compose ps
check_status.bat
```

### View Logs
```bash
docker logs <container_name>
docker compose logs -f
```

### Restart Service
```bash
docker compose restart orchestrator
```

### Stop Everything
```bash
docker compose down
```

### Reset Everything
```bash
cleanup_lucy.bat
```

---

## 🚨 If Something Fails

**Step 1:** Check logs
```bash
docker logs <service_name> | tail -50
```

**Step 2:** Check compose validity
```bash
docker compose config
```

**Step 3:** Restart service
```bash
docker compose restart <service_name>
```

**Step 4:** Full reset if needed
```bash
cleanup_lucy.bat
start_lucy_fixed.bat
```

---

## 📝 Setup Checklist

- [ ] Infrastructure running (`docker compose ps`)
- [ ] Create Dockerfiles for each service in `Code/*/`
- [ ] Build images (`docker compose build`)
- [ ] Start full stack (`start_lucy_fixed.bat`)
- [ ] Verify health checks pass
- [ ] Test endpoints (see Port Map below)

---

## 🌐 Port Map & Access

| Service | Port | URL | Status |
|---------|------|-----|--------|
| Orchestrator | 8000 | http://localhost:8000/health | ⏳ needs Dockerfile |
| Policy Engine | 8500 | http://localhost:8500/health | ⏳ needs Dockerfile |
| Chat | 9001 | http://localhost:9001/health | ⏳ needs Dockerfile |
| Grafana | 3000 | http://localhost:3000 | ⚠️ loading |
| Prometheus | 9090 | http://localhost:9090 | ✅ ready |
| Qdrant | 6333 | http://localhost:6333/dashboard | ⚠️ initializing |
| Redis | 6379 | localhost:6379 | ✅ ready |
| Postgres | 5432 | localhost:5432 | ✅ ready |
| MinIO | 9000 | http://localhost:9000 | ✅ ready |
| NATS | 4222 | localhost:4222 | ✅ ready |

---

## ⚙️ Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full stack definition |
| `docker-compose.infrastructure.yml` | Infrastructure only |
| `start_lucy_fixed.bat` | Phased startup |
| `check_status.bat` | Status checker |
| `cleanup_lucy.bat` | Container cleanup |
| `debug_lucy.bat` | Diagnostics |
| `Code/Dockerfile.template` | Service Dockerfile template |
| `DOCKER_SETUP.md` | Detailed setup guide |
| `TROUBLESHOOTING.md` | Troubleshooting guide |

---

## ⚡ Performance Tips

1. **Start infrastructure first, then custom services**
   ```bash
   docker compose -f docker-compose.infrastructure.yml up -d
   # Wait 30 seconds, then:
   docker compose build
   docker compose up -d
   ```

2. **Monitor resource usage**
   ```bash
   docker stats
   ```

3. **Free up space if needed**
   ```bash
   docker system prune -a --volumes
   ```

---

## 🆘 Emergency Commands

```bash
# Stop everything
docker compose down

# Remove all containers
docker compose down --remove-orphans

# Remove old Lucy containers specifically
cleanup_lucy.bat

# Full reset
docker system prune -a --volumes

# Check what's taking space
docker system df
```

---

## 📋 Next Steps

1. **Create Dockerfiles** - Required for custom services
   - Copy `Code/Dockerfile.template` → `Code/<service>/Dockerfile`
   - Customize for Python/Node.js

2. **Build images**
   ```bash
   docker compose build
   ```

3. **Start full stack**
   ```bash
   start_lucy_fixed.bat
   ```

4. **Monitor startup**
   ```bash
   docker compose logs -f
   ```

5. **Verify all healthy**
   ```bash
   check_status.bat
   ```

---

## 💡 Pro Tips

- Use `docker compose pull` to pre-download public images
- Use `docker compose build --parallel` to speed up builds
- Enable volume mount caching for faster file access
- Use `docker stats --no-stream` for one-time resource check
- Set resource limits in docker-compose.yml for predictable behavior

---

**Need help?** Check `TROUBLESHOOTING.md` or `DOCKER_SETUP.md`
