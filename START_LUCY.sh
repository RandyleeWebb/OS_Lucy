#!/bin/bash

# Lucy's Controlled Startup Script
# Starts services in layers, waiting for health before proceeding

set -e

COMPOSE_FILE="docker-compose.yml"
TIMEOUT=120
CHECK_INTERVAL=5

echo "🚀 Starting Lucy's ecosystem with controlled rollout..."

# Function to wait for services
wait_for_services() {
    local service_names=("$@")
    local elapsed=0
    
    echo "⏳ Waiting for: ${service_names[*]}"
    
    while [ $elapsed -lt $TIMEOUT ]; do
        local all_healthy=true
        
        for service in "${service_names[@]}"; do
            local state=$(docker compose ps "$service" --format "{{.State}}" 2>/dev/null || echo "")
            if [ "$state" != "running" ]; then
                all_healthy=false
                break
            fi
        done
        
        if [ "$all_healthy" = true ]; then
            echo "✅ All services healthy: ${service_names[*]}"
            return 0
        fi
        
        sleep $CHECK_INTERVAL
        elapsed=$((elapsed + CHECK_INTERVAL))
    done
    
    echo "⚠️  Timeout waiting for services after ${TIMEOUT}s"
    return 1
}

# Layer 1: Core Infrastructure
echo "📦 Layer 1: Starting core infrastructure..."
docker compose up -d redis postgres minio qdrant nats prometheus grafana ollama
wait_for_services "redis" "postgres" "minio" "qdrant" "nats" "prometheus" "grafana" "ollama"

# Layer 2: Policy & Vault Foundation
echo "🔐 Layer 2: Starting policy & vault foundation..."
docker compose up -d policy_engine ledger vault_api
wait_for_services "policy_engine" "ledger" "vault_api"

# Layer 3: Executor & Memory Systems
echo "🧠 Layer 3: Starting executor & memory systems..."
docker compose up -d executor_api entity_extractor graph_engine memory_engine
wait_for_services "executor_api" "entity_extractor" "graph_engine" "memory_engine"

# Layer 4: Core Orchestration
echo "⚙️  Layer 4: Starting core orchestration..."
docker compose up -d orchestrator registry message-bus
wait_for_services "orchestrator" "registry" "message-bus"

# Layer 5: Services & Utilities
echo "🛠️  Layer 5: Starting services & utilities..."
docker compose up -d sentinel scout vector-store object-storage ollama_service embedding pruning retrieval episodic-db datavault
wait_for_services "sentinel" "scout" "vector-store" "object-storage" "ollama_service" "embedding"

# Layer 6: Advanced Systems
echo "🎯 Layer 6: Starting advanced systems..."
docker compose up -d cognition_loop
wait_for_services "cognition_loop"

docker compose up -d lucy_chat
wait_for_services "lucy_chat"

docker compose up -d forge
wait_for_services "forge"

docker compose up -d planner threat_intel aegis
wait_for_services "planner" "threat_intel" "aegis"

# Layer 7: Safeguard & Compliance
echo "🛡️  Layer 7: Starting safeguard & compliance..."
docker compose up -d ast_validator cryptographic_rules gravity_model merkle_tree wal signatures governance_daemon hash_chain_verifier kill_switch
wait_for_services "governance_daemon" "hash_chain_verifier" "kill_switch"

# Layer 8: Homeostasis & Observability
echo "📊 Layer 8: Starting homeostasis & observability..."
docker compose up -d circuit_breakers chaos_injector perfmon resilience_score prometheus_exporter otel_tracing structured_logs
wait_for_services "resilience_score" "otel_tracing" "structured_logs"

# Layer 9: Terminal Services
echo "🎬 Layer 9: Starting terminal services..."
docker compose up -d wasm_runtime wasm_limits wasm_host_functions archivist diagnostics_recovery_cortex
wait_for_services "diagnostics_recovery_cortex"

echo ""
echo "✨ Lucy is fully operational!"
echo ""
echo "📊 Service Status:"
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🌐 Access Points:"
echo "  - Orchestrator: http://localhost:8000/health"
echo "  - Chat: http://localhost:9001/health"
echo "  - Grafana: http://localhost:3000"
echo "  - Prometheus: http://localhost:9090"
