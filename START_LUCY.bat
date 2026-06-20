@echo off
REM Lucy's Controlled Startup Script (Windows)
REM Starts services in layers, waiting for health before proceeding

setlocal enabledelayedexpansion

set COMPOSE_FILE=docker-compose.yml
set TIMEOUT=120
set CHECK_INTERVAL=5

echo.
echo 🚀 Starting Lucy's ecosystem with controlled rollout...
echo.

:layer1
echo 📦 Layer 1: Starting core infrastructure...
docker compose up -d redis postgres minio qdrant nats prometheus grafana ollama
timeout /t 15 /nobreak

:layer2
echo.
echo 🔐 Layer 2: Starting policy and vault foundation...
docker compose up -d policy_engine ledger vault_api
timeout /t 15 /nobreak

:layer3
echo.
echo 🧠 Layer 3: Starting executor and memory systems...
docker compose up -d executor_api entity_extractor graph_engine memory_engine
timeout /t 15 /nobreak

:layer4
echo.
echo ⚙️  Layer 4: Starting core orchestration...
docker compose up -d orchestrator registry message-bus
timeout /t 15 /nobreak

:layer5
echo.
echo 🛠️  Layer 5: Starting services and utilities...
docker compose up -d sentinel scout vector-store object-storage ollama_service embedding pruning retrieval episodic-db datavault
timeout /t 20 /nobreak

:layer6
echo.
echo 🎯 Layer 6: Starting advanced systems...
docker compose up -d cognition_loop
timeout /t 15 /nobreak

docker compose up -d lucy_chat
timeout /t 10 /nobreak

docker compose up -d forge
timeout /t 10 /nobreak

docker compose up -d planner threat_intel aegis
timeout /t 15 /nobreak

:layer7
echo.
echo 🛡️  Layer 7: Starting safeguard and compliance...
docker compose up -d ast_validator cryptographic_rules gravity_model merkle_tree wal signatures governance_daemon hash_chain_verifier kill_switch
timeout /t 20 /nobreak

:layer8
echo.
echo 📊 Layer 8: Starting homeostasis and observability...
docker compose up -d circuit_breakers chaos_injector perfmon resilience_score prometheus_exporter otel_tracing structured_logs
timeout /t 20 /nobreak

:layer9
echo.
echo 🎬 Layer 9: Starting terminal services...
docker compose up -d wasm_runtime wasm_limits wasm_host_functions archivist diagnostics_recovery_cortex
timeout /t 20 /nobreak

echo.
echo ✨ Lucy is fully operational!
echo.
echo 📊 Service Status:
docker compose ps

echo.
echo 🌐 Access Points:
echo   - Orchestrator: http://localhost:8000/health
echo   - Chat: http://localhost:9001/health
echo   - Grafana: http://localhost:3000
echo   - Prometheus: http://localhost:9090
echo.

pause
