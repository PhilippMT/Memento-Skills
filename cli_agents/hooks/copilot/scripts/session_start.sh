#!/bin/bash
# Memento-Skills: Session Start Hook for GitHub Copilot CLI
#
# This hook runs when a Copilot CLI session starts. It:
# 1. Ensures the Memento ACP server is running
# 2. Syncs skills to the Copilot-native format
# 3. Warms the skill cache
#
# Input (JSON via stdin):
#   { "timestamp": ..., "cwd": "...", "source": "new"|"resume", "initialPrompt": "..." }
#
# Output: ignored
set -e

INPUT=$(cat)
MEMENTO_URL="http://${MEMENTO_ACP_HOST:-127.0.0.1}:${MEMENTO_ACP_PORT:-47200}"

# ---- 1. Ensure ACP server is running ----
health=$(curl -s --max-time 3 "${MEMENTO_URL}/health" 2>/dev/null || echo "")

if [ -z "$health" ] || ! echo "$health" | grep -q '"status":"ok"'; then
    # Try to start the server
    if command -v memento &>/dev/null; then
        memento serve --daemon &>/dev/null || true
        # Wait for startup
        for i in $(seq 1 10); do
            sleep 0.5
            health=$(curl -s --max-time 2 "${MEMENTO_URL}/health" 2>/dev/null || echo "")
            if echo "$health" | grep -q '"status":"ok"'; then
                break
            fi
        done
    fi
fi

# ---- 2. Sync skills to Copilot format ----
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

curl -s --max-time 10 -X POST "${MEMENTO_URL}/sync" \
    -H "Content-Type: application/json" \
    -d "{\"target\": \"copilot-cli\", \"workspace\": \"${CWD}\"}" \
    >/dev/null 2>&1 || true

# ---- 3. Log session start ----
SOURCE=$(echo "$INPUT" | jq -r '.source // "unknown"')
TIMESTAMP=$(echo "$INPUT" | jq -r '.timestamp // 0')

echo "[memento] Session started (source=${SOURCE}) at $(date -d @$((TIMESTAMP/1000)) 2>/dev/null || date)" >&2

exit 0
