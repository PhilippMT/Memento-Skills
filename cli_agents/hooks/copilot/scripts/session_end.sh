#!/bin/bash
# Memento-Skills: Session End Hook for GitHub Copilot CLI
#
# This hook runs when a Copilot CLI session ends. It:
# 1. Triggers final reflection on the session
# 2. Persists learning data
# 3. Logs session completion
#
# Input (JSON via stdin):
#   { "timestamp": ..., "cwd": "...", "reason": "complete"|"error"|"abort"|"timeout"|"user_exit" }
#
# Output: ignored
set -e

INPUT=$(cat)
MEMENTO_URL="http://${MEMENTO_ACP_HOST:-127.0.0.1}:${MEMENTO_ACP_PORT:-47200}"

REASON=$(echo "$INPUT" | jq -r '.reason // "unknown"')

# ---- 1. Record session end ----
curl -s --max-time 5 -X POST "${MEMENTO_URL}/reflect" \
    -H "Content-Type: application/json" \
    -d "{
        \"tool_name\": \"_session\",
        \"result_type\": \"${REASON}\",
        \"result_text\": \"Session ended with reason: ${REASON}\"
    }" >/dev/null 2>&1 || true

# ---- 2. Log session end ----
echo "[memento] Session ended (reason=${REASON})" >&2

exit 0
