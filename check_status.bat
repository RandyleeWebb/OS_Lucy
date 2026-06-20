@echo off
REM Lucy's Quick Status Check (Windows)

cls
echo.
echo 📊 Lucy's Current Status Report
echo ===============================
echo.

echo ✅ Running Containers:
docker ps --filter "status=running" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>nul | find /v "NAMES" || echo (none)
echo.

echo ⚠️  Unhealthy/Starting Containers:
docker ps --filter "health=unhealthy" --format "table {{.Names}}\t{{.Status}}" 2>nul | find /v "NAMES" || echo (none)
echo.

echo ❌ Exited Containers (last 5):
docker ps -a --filter "status=exited" --format "{{.Names}}: {{.Status}}" | head -5 2>nul || echo (none)
echo.

echo 🌐 Infrastructure Ports:
echo   - Redis:       redis://localhost:6379
echo   - Postgres:    postgres://localhost:5432
echo   - Minio:       http://localhost:9000
echo   - Qdrant:      http://localhost:6333
echo   - NATS:        nats://localhost:4222
echo   - Prometheus:  http://localhost:9090
echo   - Grafana:     http://localhost:3000
echo   - Ollama:      http://localhost:11434
echo.

echo 📋 Docker System Info:
docker system df 2>nul | find /v "Reclaimed"
echo.

echo 💾 Disk Usage:
docker system df --format "table" 2>nul | head -5
echo.

pause
