#!/usr/bin/env bash
# Pre-flight check: is the proxy up, does it list models, does a chat request work?
set -euo pipefail

BASE="${PRIVATEMODE_BASE_URL:-http://localhost:8080}"
MODEL="${PRIVATEMODE_MODEL:-glm-latest}"

echo "== models at $BASE/v1/models"
curl -fsS --max-time 20 "$BASE/v1/models" | python3 -c '
import json, sys
for m in json.load(sys.stdin).get("data", []):
    print(" ", m["id"])
'

echo "== chat request ($MODEL)"
curl -fsS --max-time 120 "$BASE/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "{\"model\": \"$MODEL\", \"max_tokens\": 2048, \"reasoning_effort\": \"low\",
       \"messages\": [{\"role\": \"user\", \"content\": \"Reply with the single word: ready\"}]}" \
  | python3 -c '
import json, sys
r = json.load(sys.stdin)
print(" ", (r["choices"][0]["message"].get("content") or "").strip())
'
echo "ok"
