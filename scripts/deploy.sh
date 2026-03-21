#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# deploy.sh — Pull latest code and redeploy the stack
# Run from the project root: /opt/war-of-names
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="/opt/war-of-names"
cd "$APP_DIR"

echo "═══ War of Names — Deploy ═══"
echo ""

# 1. Pull latest code
echo "→ Pulling latest code from GitHub..."
git pull origin main

# 2. Build and restart containers
echo "→ Building and restarting containers..."
docker compose up -d --build

# 3. Wait for health
echo "→ Waiting for API health..."
for i in $(seq 1 30); do
    if docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
        echo "  ✓ API healthy"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ✗ API did not become healthy in 30 attempts"
        echo "  Check logs: docker compose logs api"
        exit 1
    fi
    sleep 2
done

# 4. Verify
echo ""
echo "→ Verification:"
echo "  Containers:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "  Health check:"
curl -sf http://127.0.0.1:8080/health && echo ""
echo ""
echo "═══ Deploy complete ═══"
