#!/usr/bin/env bash
# The same request with curl. Needs the Privatemode proxy on localhost:8080 (make proxy).
curl -sS http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "glm-latest",
    "reasoning_effort": "low",
    "messages": [{"role": "user", "content": "Explain remote attestation in two sentences."}]
  }'
