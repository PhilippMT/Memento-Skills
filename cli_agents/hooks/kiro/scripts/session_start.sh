#!/usr/bin/env bash
# agentSpawn hook — ensure ACP server is running and sync skills.
# STDIN: JSON with hook_event_name, cwd
# STDOUT: added to agent context on exit 0
set -e

INPUT=$(cat)
HOST="${MEMENTO_ACP_HOST:-127.0.0.1}"
PORT="${MEMENTO_ACP_PORT:-47200}"
BASE="http://${HOST}:${PORT}"
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

# Check ACP health
health=$(curl -sf --max-time 3 "${BASE}/health" 2>/dev/null || true)
if ! echo "$health" | jq -e '.status == "ok"' >/dev/null 2>&1; then
  echo "[memento] ACP server not reachable at ${BASE}. Start with: memento serve --daemon"
  exit 0
fi

# Sync skills
curl -sf --max-time 10 -X POST "${BASE}/sync" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg target kiro --arg workspace "$CWD" \
    '{target: $target, workspace: $workspace}')" >/dev/null 2>&1 || true

echo "[memento] ACP connected at ${BASE}. Skills synced for workspace: ${CWD}"
