#!/usr/bin/env bash
# Smoke test E2E del backend.
# Asume:
#   - uvicorn corriendo en :8000 (make dev-api)
#   - Si SYNC_MODE=0: redis (make dev-redis) + worker (make dev-worker)
#   - Existe al menos un PDF en PDAs/
#
# Verifica: register -> login -> upload -> poll status -> download.

set -euo pipefail

API="${API:-http://localhost:8000}"
EMAIL="smoke-$(date +%s)@test.local"
PASSWORD="smoketest1234"
PDF=$(ls PDAs/*.pdf 2>/dev/null | head -n1 || true)

if [[ -z "$PDF" ]]; then
    echo "ERROR: no se encontro ningun PDF en PDAs/"
    exit 1
fi

echo "[smoke] health"
curl -fsS "$API/api/health" | tee /dev/stderr; echo

echo "[smoke] register $EMAIL"
TOKEN=$(curl -fsS -X POST "$API/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "[smoke] token=${TOKEN:0:20}..."

echo "[smoke] me"
curl -fsS "$API/api/auth/me" -H "Authorization: Bearer $TOKEN" | tee /dev/stderr; echo

echo "[smoke] upload $PDF"
ID=$(curl -fsS -X POST "$API/api/analyses" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$PDF" \
    -F "codigo_curso=22A14" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "[smoke] analysis_id=$ID"

echo "[smoke] polling status..."
for i in $(seq 1 60); do
    STATUS=$(curl -fsS "$API/api/analyses/$ID" -H "Authorization: Bearer $TOKEN" \
        | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
    echo "  [$i] status=$STATUS"
    if [[ "$STATUS" == "done" || "$STATUS" == "failed" ]]; then
        break
    fi
    sleep 5
done

if [[ "$STATUS" != "done" ]]; then
    echo "ERROR: status final=$STATUS"
    exit 1
fi

echo "[smoke] download report"
curl -fsS "$API/api/analyses/$ID/download" -H "Authorization: Bearer $TOKEN" -o /tmp/smoke_report.json
echo "[smoke] reporte guardado en /tmp/smoke_report.json ($(wc -c < /tmp/smoke_report.json) bytes)"

echo "[smoke] OK"
