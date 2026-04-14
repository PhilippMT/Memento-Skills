#!/bin/bash
# Memento-Skills: Session End Hook for GitHub Copilot CLI
# Input (JSON via stdin): { "timestamp": ..., "cwd": "...", "reason": "complete"|"error"|"abort"|"timeout"|"user_exit" }
# Output: ignored
set -e

INPUT=$(cat)
MEMENTO_URL="http://${MEMENTO_ACP_HOST:-127.0.0.1}:${MEMENTO_ACP_PORT:-47200}"

REASON=$(echo "$INPUT" | jq -r '.reason // "unknown"')

# ---- 1. Record session end ----
curl -s --max-time 5 -X POST "${MEMENTO_URL}/reflect" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg reason "$REASON" '{tool_name: "_session", result_type: $reason, result_text: ("Session ended with reason: " + $reason)}')" \
    >/dev/null 2>&1 || true

# ---- 2. Log session end ----
echo "[memento] Session ended (reason=${REASON})" >&2

exit 0
