#!/usr/bin/env bash
# stop hook — record session end.
# STDIN: JSON with hook_event_name, cwd, assistant_response
set -e

INPUT=$(cat)
HOST="${MEMENTO_ACP_HOST:-127.0.0.1}"
PORT="${MEMENTO_ACP_PORT:-47200}"
BASE="http://${HOST}:${PORT}"

curl -sf --max-time 5 -X POST "${BASE}/reflect" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg tool_name "session_end" \
    --arg result_type "success" \
    --arg result_text "Session ended"  \
    '{tool_name: $tool_name, result_type: $result_type, result_text: $result_text}')" \
  >/dev/null 2>&1 || true

exit 0
