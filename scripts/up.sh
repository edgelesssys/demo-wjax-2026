#!/usr/bin/env bash
# One command before the talk: start the proxy in the background, wait until it answers, run the
# pre-flight check and show the attestation lines from the proxy log.
#
#   make up      start (or reuse) the proxy, then check
#   make logs    show the proxy log again, e.g. on stage
#   make down    stop the proxy
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="${PRIVATEMODE_BASE_URL:-http://localhost:8080}"

docker info >/dev/null 2>&1 || { echo "Docker is not running. Start Docker Desktop and try again." >&2; exit 1; }

if docker ps --format '{{.Names}}' | grep -qx privatemode-proxy; then
  echo "proxy already running (container privatemode-proxy)"
else
  # Another program on port 8080 (for example the Privatemode Proxy desktop app) blocks the container.
  if lsof -nP -iTCP:8080 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port 8080 is already in use by:" >&2
    lsof -nP -iTCP:8080 -sTCP:LISTEN >&2
    echo "Quit that program (e.g. the Privatemode Proxy app) and run make up again." >&2
    exit 1
  fi
  PROXY_DETACH=1 scripts/proxy.sh >/dev/null
  echo "proxy starting ..."
fi

for _ in $(seq 1 40); do
  curl -fsS --max-time 2 "$BASE/v1/models" >/dev/null 2>&1 && break
  sleep 2
done
curl -fsS --max-time 2 "$BASE/v1/models" >/dev/null 2>&1 \
  || { echo "proxy did not come up, see: docker logs privatemode-proxy" >&2; exit 1; }

scripts/check.sh

echo
echo "== attestation (from the proxy log)"
docker logs privatemode-proxy 2>&1 \
  | grep -E "manifest fetched|verified report signature|Validate succeeded|Secret updated" \
  | sed -E 's/^time=([^ ]+) level=INFO msg="?([^"]*)"?.*/  \1  \2/' \
  | cut -c1-140
echo
echo "ready: the proxy listens on $BASE"
