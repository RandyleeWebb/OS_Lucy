@echo off
REM Lucy's Startup Debugging Guide (Windows)

echo.
echo 🔍 Lucy's Docker Compose Debug Report
echo ======================================
echo.

REM 1. Check compose file status
echo 1️⃣  Compose File Validation:
docker compose config > nul 2>&1
if %errorlevel% equ 0 (
    echo    ✅ docker-compose.yml is valid
) else (
    echo    ❌ docker-compose.yml has errors
)
echo.

REM 2. Check running containers
echo 2️⃣  Container Status:
echo    Running:
docker ps --format "table {{.Names}}\t{{.Status}}"
echo.
echo    Exited/Stopped (sample):
docker ps -a --filter status=exited --format "table {{.Names}}\t{{.Status}}" | find /v "NAMES" | head -10
echo.

REM 3. Check infrastructure services
echo 3️⃣  Infrastructure Services Health:
for %%S in (redis postgres minio qdrant nats prometheus grafana ollama) do (
    docker inspect --format="{{.State.Running}}" %%S >nul 2>&1
    if !errorlevel! equ 0 (
        echo    ✅ %%S: running
    ) else (
        echo    ❌ %%S: not running or doesn't exist
    )
)
echo.

REM 4. Check for Dockerfiles
echo 4️⃣  Checking for Dockerfiles:
setlocal enabledelayedexpansion
set missing=0
for /d %%D in (Code\*) do (
    if not exist "%%D\Dockerfile" (
        echo    ⚠️  %%D\Dockerfile NOT FOUND
        set /a missing=!missing!+1
    )
)
if !missing! equ 0 (
    echo    ✅ All Dockerfiles present
) else (
    echo    ⚠️  !missing! services missing Dockerfiles
)
endlocal
echo.

REM 5. Disk space
echo 5️⃣  Docker System Resources:
docker system df
echo.

REM 6. Recent errors
echo 6️⃣  Recent Container Errors:
docker ps -a --filter "status=exited" --format "{{.Names}}: {{.Status}}" | head -5
echo.

REM 7. Next steps
echo 📋 NEXT STEPS:
echo    1. Create Dockerfiles for each service in Code\*\ directories
echo       - Use: Code\Dockerfile.template as a reference
echo    2. For services with no Dockerfile, copy template and customize
echo    3. Run: docker compose build
echo    4. Run: docker compose up -d
echo.
echo 🚀 QUICK START (Infrastructure only):
echo    docker compose -f docker-compose.infrastructure.yml up -d
echo.

pause
