# Lucy Docker Troubleshooting Guide

## Quick Diagnostics

### Status Check
```batch
check_status.bat
```
Shows all running/exited containers and open ports.

---

## Common Issues & Fixes

### Issue: "Startup Failed Halfway"

**Symptom:** Some containers start, others fail or don't start.

**Causes & Fixes:**

1. **Missing Dockerfiles** (most common)
   ```bash
   # Check which services are missing Dockerfiles
   dir Code\*\Dockerfile
   
   # Copy template for each missing service
   copy Code\Dockerfile.template Code\<service>\Dockerfile
   ```

2. **Port Already in Use**
   ```powershell
   # Find what's using the port
   netstat -ano | findstr :8000
   Get-Process -Id <PID>
   
   # Or kill Docker and restart
   docker system prune -a
   ```

3. **Out of Disk Space**
   ```bash
   docker system df
   # If >80% used, run cleanup_lucy.bat
   ```

4. **Out of Memory**
   ```bash
   docker stats --no-stream
   # Increase Docker Desktop memory limit in Settings
   ```

---

### Issue: Containers Show "Unhealthy"

**Example:** `postgres (health: starting)` after 5+ minutes

**Causes & Fixes:**

1. **Service Takes Too Long to Start**
   - Increase `start_period` in healthcheck
   - Example: `start_period: 60s` instead of `10s`

2. **Health Check Endpoint Fails**
   ```bash
   # Test manually
   docker exec postgres pg_isready -U postgres
   docker exec redis redis-cli ping
   docker exec qdrant curl http://localhost:6333/healthz
   ```

3. **Service Crashed**
   ```bash
   docker logs postgres | tail -50
   # Look for errors like missing volumes, permission issues, etc.
   ```

---

### Issue: PowerShell Script Errors

**Common errors:**

```
Cannot find path
At line:1 char:1 + docker ...
```

**Fix:** Run as Administrator
```powershell
# Right-click PowerShell → Run as Administrator
# Then run scripts
.\start_lucy_fixed.bat
.\cleanup_lucy.bat
```

---

### Issue: "docker: command not found"

**Causes:**
- Docker not installed
- Docker Desktop not running
- Path not set

**Fixes:**
```bash
# Check if Docker is installed
docker --version

# Restart Docker Desktop (Windows)
# Or start Docker daemon (Linux)
sudo systemctl restart docker

# Check Docker daemon
docker ps
```

---

### Issue: Containers Exit Immediately

**Symptom:** Container status shows "Exited (1)" within seconds

**Fix: Check logs**
```bash
docker logs <container_name>

# Common patterns:
# - "No such file or directory" → Missing Dockerfile or entrypoint
# - "ModuleNotFoundError" → Missing Python package
# - "npm ERR!" → Missing Node dependencies
# - "Cannot connect to" → Dependency service not running
```

---

### Issue: Network Connection Failed

**Symptom:** "Cannot connect to orchestrator" or similar

**Fix: Verify Network**
```bash
# List networks
docker network ls

# Inspect network
docker network inspect lucy_net

# Test connectivity
docker exec <service> ping <other_service>
docker exec orchestrator curl http://policy_engine:8500/health
```

---

### Issue: Port Conflicts

**Symptom:** `bind: address already in use`

**Fix:**
```bash
# Find what's using the port
netstat -ano | findstr :8000
Get-Process -Id <PID>

# Either stop that process or change docker-compose port
# In docker-compose.yml: 8001:8000 (host:container)
```

---

## Step-by-Step Recovery

### If Startup Failed Halfway:

**1. Check what's running**
```bash
docker compose ps
```

**2. View logs of failed services**
```bash
docker logs <service_name>
```

**3. Clean up and restart**
```bash
# Option A: Soft restart (keep volumes)
docker compose restart

# Option B: Hard restart (remove containers, keep images)
docker compose down
docker compose up -d

# Option C: Full reset (remove everything)
cleanup_lucy.bat
# Then: start_lucy_fixed.bat
```

**4. Monitor startup**
```bash
# Watch in real-time
docker compose logs -f

# Or periodic check
:loop
cls
docker compose ps
timeout /t 5
goto loop
```

---

## Verification Checklist

After startup completes, verify each layer:

### Layer 1: Infrastructure ✅
```bash
curl http://localhost:6333/healthz   # Qdrant
curl http://localhost:9000/minio/health/live  # MinIO
redis-cli -p 6379 ping               # Redis
psql -U postgres -h localhost        # Postgres
```

### Layer 2: API Services ✅
```bash
curl http://localhost:8000/health    # Orchestrator
curl http://localhost:8500/health    # Policy Engine
curl http://localhost:8604/health    # Vault API
```

### Layer 3: Advanced Services ✅
```bash
curl http://localhost:9000/health    # Cognition Loop
curl http://localhost:9001/health    # Chat
curl http://localhost:9003/health    # Planner
```

---

## Recovery Commands

### Stop Everything Safely
```bash
docker compose down
```

### Remove All Lucy Containers
```bash
docker compose down --remove-orphans
cleanup_lucy.bat  # option 2
```

### Free Up Disk Space
```bash
docker system prune -a --volumes
```

### View All Logs
```bash
docker compose logs --tail=100 -f
```

### Restart Specific Service
```bash
docker compose restart orchestrator
docker logs orchestrator -f
```

---

## Emergency Contacts

If you get stuck:

1. **Check logs first**
   ```bash
   docker logs <container> 2>&1 | tail -50
   ```

2. **Check Docker Desktop Settings**
   - Memory limit (should be ≥8GB)
   - Disk space (should be >50GB free)

3. **Try full reset**
   ```bash
   cleanup_lucy.bat  # option 3
   docker image prune -a
   docker system prune -a --volumes
   # Then restart Docker Desktop
   ```

4. **Check compose file syntax**
   ```bash
   docker compose config
   ```

---

## Performance Tips

1. **Reduce startup time:**
   - Use `docker compose pull` to pre-download images
   - Build images separately: `docker compose build`

2. **Monitor resource usage:**
   ```bash
   docker stats --no-stream
   ```

3. **Enable volume mount caching (Mac/Windows):**
   ```yml
   volumes:
     - ./src:/app/src:cached
   ```

4. **Use multi-stage builds** for smaller images

---

## Files Reference

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full stack (requires all Dockerfiles) |
| `docker-compose.infrastructure.yml` | Infrastructure only (works now) |
| `start_lucy_fixed.bat` | Phased startup script |
| `check_status.bat` | View current status |
| `cleanup_lucy.bat` | Remove/reset containers |
| `debug_lucy.bat` | Automated diagnostics |
| `Code/Dockerfile.template` | Template for creating service Dockerfiles |
| `DOCKER_SETUP.md` | Setup guide |
| `TROUBLESHOOTING.md` | This file |

---

## Still Stuck?

Provide these details:

1. **What's running?**
   ```bash
   docker compose ps
   ```

2. **What failed?**
   ```bash
   docker logs <container> 2>&1
   ```

3. **System info:**
   ```bash
   docker system df
   docker stats --no-stream
   ```

4. **Compose config:**
   ```bash
   docker compose config 2>&1 | head -20
   ```
