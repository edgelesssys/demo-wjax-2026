#!/usr/bin/env bash
# Start the Privatemode proxy on 127.0.0.1:8080.
#
# The proxy runs on your machine. It checks the attestation of the Privatemode deployment
# before it sends anything, and encrypts prompts before they leave the machine. Your tools
# (Claude Code, OpenCode, your own code) talk plain HTTP to localhost.
#
# The API key is read from a file instead of the command line, so it does not show up in
# `ps` or `docker inspect`. Create the file once with `make key` (how to get a key: README).
set -euo pipefail
cd "$(dirname "$0")/.."

# Pin the image. Flag names changed between releases (--apiKey became --api-key in v1.60),
# and `latest` may be an old image already cached on your machine.
IMAGE="${PROXY_IMAGE:-ghcr.io/edgelesssys/privatemode/privatemode-proxy:v1.60.0}"
KEY_FILE="${KEY_FILE:-$PWD/.privatemode-api-key}"

[ -s "$KEY_FILE" ] || { echo "missing $KEY_FILE. Get a key (see README, \"Get an API key\") and run: make key" >&2; exit 1; }

# Do not use --dump-requests here: it writes prompts to disk in plaintext.
# PROXY_DETACH=1 runs the container in the background (that is what `make up` does).
exec docker run ${PROXY_DETACH:+-d} --rm --name privatemode-proxy \
  -p 127.0.0.1:8080:8080 \
  -v "$KEY_FILE:/secrets/api-key:ro" \
  "$IMAGE" \
  --api-key @/secrets/api-key \
  --api-key-fallback=always \
  --disable-prompt-cache=false
