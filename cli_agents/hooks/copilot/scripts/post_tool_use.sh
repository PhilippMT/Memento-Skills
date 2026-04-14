#!/bin/bash
# Memento-Skills: Post-Tool-Use Hook for GitHub Copilot CLI
# Input (JSON via stdin): { "timestamp": ..., "toolName": "...", "toolResult": { "resultType": "...", "textResultForLlm": "..." } }
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
    -d "$(jq -n --arg tool "$TOOL_NAME" --arg type "$RESULT_TYPE" --arg text "$RESULT_TEXT" '{tool_name: $tool, result_type: $type, result_text: $text}')" \
    >/dev/null 2>&1 || true

# ---- 2. Log execution statistics ----
echo "[memento] Tool ${TOOL_NAME}: ${RESULT_TYPE}" >&2

exit 0
