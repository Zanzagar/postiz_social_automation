#!/usr/bin/env bash
# Health check for Postiz infrastructure
# Usage: ./scripts/postiz-health-check.sh

set -euo pipefail

POSTIZ_URL="${POSTIZ_URL:-https://postiz.sethpc.xyz}"
N8N_URL="${N8N_URL:-https://n8n.sethpc.xyz}"

check_service() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"

    http_code=$(curl -sf -o /dev/null -w "%{http_code}" -L "$url" 2>/dev/null || echo "000")

    if [ "$http_code" = "$expected_code" ]; then
        echo "OK   $name ($url) — HTTP $http_code"
        return 0
    else
        echo "FAIL $name ($url) — HTTP $http_code (expected $expected_code)"
        return 1
    fi
}

echo "=== Postiz Infrastructure Health Check ==="
echo "Date: $(date -Iseconds)"
echo ""

failures=0

check_service "Postiz Dashboard" "$POSTIZ_URL/" || ((failures++))
check_service "Postiz API"       "$POSTIZ_URL/api/" || ((failures++))
check_service "n8n"              "$N8N_URL/" || ((failures++))

echo ""
if [ "$failures" -eq 0 ]; then
    echo "All services healthy."
else
    echo "$failures service(s) failed health check."
    exit 1
fi
