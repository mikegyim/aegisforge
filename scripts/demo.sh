#!/usr/bin/env bash
# End-to-end local demo. Spins the API, fires three representative events,
# pretty-prints the incident analysis, then opens the dry-run PR proposal.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${AEGIS_API_BASE:-http://localhost:8000}"
KEY_HDR=()
if [[ -n "${AEGIS_API_KEY:-}" ]]; then
  KEY_HDR=(-H "X-API-Key: ${AEGIS_API_KEY}")
fi

post() {
  local payload="$1"
  curl -sS -X POST "${API}/events" \
    -H "Content-Type: application/json" \
    "${KEY_HDR[@]}" \
    -d @"$payload"
}

echo "[1/3] CI memory pressure -------------------------------------------------"
RESP1=$(post "$ROOT/examples/events/node-memory-pressure.json")
echo "$RESP1" | python3 -m json.tool
ID1=$(echo "$RESP1" | python3 -c "import sys,json;print(json.load(sys.stdin)['incident_id'])")

echo
echo "[2/3] Falco reverse shell -----------------------------------------------"
post "$ROOT/examples/events/falco-shell-event.json" | python3 -m json.tool

echo
echo "[3/3] Cost anomaly ------------------------------------------------------"
post "$ROOT/examples/events/cost-anomaly.json" | python3 -m json.tool

echo
echo "Dry-run pull-request proposal for incident $ID1 -------------------------"
curl -sS -X POST "${API}/incidents/${ID1}/pull-request" "${KEY_HDR[@]}" | python3 -m json.tool
