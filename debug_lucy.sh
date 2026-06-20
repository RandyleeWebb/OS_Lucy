#!/bin/bash
# Lucy's Startup Debugging Guide

echo "🔍 Lucy's Docker Compose Debug Report"
echo "======================================"
echo ""

# 1. Check compose file status
echo "1️⃣  Compose File Validation:"
docker compose config > /dev/null 2>&1 && echo "   ✅ docker-compose.yml is valid" || echo "   ❌ docker-compose.yml has errors"
echo ""

# 2. Check running containers
echo "2️⃣  Container Status:"
echo "   Running:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -v NAMES || echo "   (none)"
echo ""
echo "   Exited/Stopped:"
docker ps -a --filter status=exited --format "table {{.Names}}\t{{.Status}}" | head -10 || echo "   (none)"
echo ""

# 3. Check infrastructure services
echo "3️⃣  Infrastructure Services Health:"
for service in redis postgres minio qdrant nats prometheus grafana ollama; do
  state=$(docker inspect --format='{{.State.Running}}' $service 2>/dev/null)
  if [ "$state" = "true" ]; then
    echo "   ✅ $service: running"
  else
    echo "   ❌ $service: not running or doesn't exist"
  fi
done
echo ""

# 4. Check for missing Dockerfiles
echo "4️⃣  Missing Dockerfiles (requires build):"
missing=0
for dir in Code/*/; do
  service_name=$(basename "$dir")
  if [ ! -f "$dir/Dockerfile" ]; then
    echo "   ⚠️  Code/$service_name/Dockerfile NOT FOUND"
    missing=$((missing + 1))
  fi
done
[ $missing -eq 0 ] && echo "   ✅ All Dockerfiles present" || echo "   ⚠️  $missing services missing Dockerfiles"
echo ""

# 5. Check disk space
echo "5️⃣  Docker System Resources:"
docker system df
echo ""

# 6. Recent errors
echo "6️⃣  Recent Container Errors (last 5 min):"
docker ps -a --filter "status=exited" --format "{{.Names}}: {{.Status}}" | head -5
echo ""

# 7. Next steps
echo "📋 NEXT STEPS:"
echo "   1. Create Dockerfiles for each service in Code/*/ directories"
echo "      - Use: Code/Dockerfile.template as a reference"
echo "   2. For services with no Dockerfile, copy template and customize"
echo "   3. Run: docker compose build"
echo "   4. Run: docker compose up -d"
echo ""
echo "🚀 QUICK START (Infrastructure only):"
echo "   docker compose -f docker-compose.infrastructure.yml up -d"
echo ""
