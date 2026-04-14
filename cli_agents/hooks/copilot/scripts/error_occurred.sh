#!/bin/bash
# Memento-Skills: Error Occurred Hook for GitHub Copilot CLI
# Input (JSON via stdin): { "timestamp": ..., "cwd": "...", "error": { "message": "...", "name": "...", "stack": "..." } }
# Output: ignored
set -e

INPUT=$(cat)
MEMENTO_URL="http://${MEMENTO_ACP_HOST:-127.0.0.1}:${MEMENTO_ACP_PORT:-47200}"

ERROR_MSG=$(echo "$INPUT" | jq -r '.error.message // "unknown error"')
ERROR_NAME=$(echo "$INPUT" | jq -r '.error.name // "UnknownError"')

# ---- 1. Record error in Memento ----
curl -s --max-time 5 -X POST "${MEMENTO_URL}/reflect" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg name "$ERROR_NAME" --arg msg "$ERROR_MSG" '{tool_name: "_error", result_type: "failure", result_text: ("[\($name)] \($msg)")}')" \
    >/dev/null 2>&1 || true

# ---- 2. Log error ----
echo "[memento] Error: [${ERROR_NAME}] ${ERROR_MSG}" >&2

exit 0
