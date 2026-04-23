#!/usr/bin/env bash
# postToolUse hook — record outcome for reflective learning.
# STDIN: JSON with hook_event_name, cwd, tool_name, tool_input, tool_response
# STDOUT: not used (exit 0 = success)
set -e

INPUT=$(cat)
HOST="${MEMENTO_ACP_HOST:-127.0.0.1}"
PORT="${MEMENTO_ACP_PORT:-47200}"
BASE="http://${HOST}:${PORT}"

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
TOOL_RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // ""')

# Determine result type from response
RESULT_TYPE="success"
if echo "$TOOL_RESPONSE" | grep -qi "error\|exception\|failed\|traceback"; then
  RESULT_TYPE="failure"
fi

curl -sf --max-time 5 -X POST "${BASE}/reflect" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg tool_name "$TOOL_NAME" \
    --arg result_type "$RESULT_TYPE" \
    --arg result_text "$TOOL_RESPONSE" \
    '{tool_name: $tool_name, result_type: $result_type, result_text: $result_text}')" \
  >/dev/null 2>&1 || true

exit 0
