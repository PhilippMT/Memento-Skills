#!/bin/bash
# Memento-Skills: Post-Tool-Use Hook for GitHub Copilot CLI
#
# This hook runs AFTER a tool completes execution. It:
# 1. Records the execution outcome in Memento for reflective learning
# 2. Updates skill utility scores based on success/failure
# 3. Logs execution statistics
#
# Input (JSON via stdin):
#   {
#     "timestamp": ...,
#     "cwd": "...",
#     "toolName": "bash"|"edit"|...,
#     "toolArgs": "{...}",
#     "toolResult": {
#       "resultType": "success"|"failure"|"denied",
#       "textResultForLlm": "..."
#     }
#   }
#
# Output: ignored
set -e

INPUT=$(cat)
MEMENTO_URL="http://${MEMENTO_ACP_HOST:-127.0.0.1}:${MEMENTO_ACP_PORT:-47200}"

TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // ""')
RESULT_TYPE=$(echo "$INPUT" | jq -r '.toolResult.resultType // "unknown"')
RESULT_TEXT=$(echo "$INPUT" | jq -r '.toolResult.textResultForLlm // ""' | head -c 500)

# ---- 1. Record outcome in Memento for reflective learning ----
curl -s --max-time 5 -X POST "${MEMENTO_URL}/reflect" \
    -H "Content-Type: application/json" \
    -d "{
        \"tool_name\": \"${TOOL_NAME}\",
        \"result_type\": \"${RESULT_TYPE}\",
        \"result_text\": $(echo "$RESULT_TEXT" | jq -Rs .)
    }" >/dev/null 2>&1 || true

# ---- 2. Log execution statistics ----
echo "[memento] Tool ${TOOL_NAME}: ${RESULT_TYPE}" >&2

exit 0
