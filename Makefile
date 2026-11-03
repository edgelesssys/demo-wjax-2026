SHELL := /bin/bash
.DEFAULT_GOAL := help
PY := .venv/bin/python

.PHONY: help setup data key proxy up down logs check claude claude-setup opencode clean

help: ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

setup: ## create the venv and install duckdb
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt

data: ## generate the synthetic warehouse (read-only afterwards)
	@test -x $(PY) || $(MAKE) setup
	@rm -f data/warehouse.duckdb
	$(PY) data/generate.py
	chmod 444 data/warehouse.duckdb

key: ## save your Privatemode API key to .privatemode-api-key (prompted, not echoed)
	@read -rsp "Privatemode API key: " k; echo; \
	  [ -n "$$k" ] || { echo "no key entered" >&2; exit 1; }; \
	  printf '%s' "$$k" > .privatemode-api-key; chmod 600 .privatemode-api-key; \
	  echo "saved .privatemode-api-key (gitignored)"

proxy: ## start the Privatemode proxy on localhost:8080 (needs .privatemode-api-key)
	scripts/proxy.sh

up: ## start the proxy in the background, wait for it, run the pre-flight check
	scripts/up.sh

down: ## stop the background proxy
	-docker stop privatemode-proxy

logs: ## show the proxy log (attestation lines at startup)
	docker logs --tail 40 privatemode-proxy

check: ## pre-flight: proxy reachable, models listed, chat request works
	scripts/check.sh

claude-setup: ## point Claude Code in this directory at the proxy
	mkdir -p .claude
	cp config/claude-code.settings.json .claude/settings.local.json
	@echo "wrote .claude/settings.local.json (gitignored). Revert: rm .claude/settings.local.json"

claude: claude-setup ## start Claude Code with Privatemode as backend
	claude

opencode: ## start OpenCode with Privatemode as backend
	PRIVATEMODE_API_KEY=placeholder opencode models --refresh privatemode-ai
	PRIVATEMODE_API_KEY=placeholder opencode

clean: ## remove generated data and agent output
	chmod u+w data/warehouse.duckdb 2>/dev/null || true
	rm -f data/warehouse.duckdb data/warehouse.duckdb.wal
	find analysis -type f ! -name .gitkeep -delete
