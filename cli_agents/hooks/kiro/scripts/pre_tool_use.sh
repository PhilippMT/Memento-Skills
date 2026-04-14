#!/usr/bin/env bash
# preToolUse hook — discover relevant skills and block dangerous commands.
# STDIN: JSON with hook_event_name, cwd, tool_name, tool_input
# STDOUT: added to agent context on exit 0; exit 2 = block tool use
set -e

INPUT=$(cat)
HOST="${MEMENTO_ACP_HOST:-127.0.0.1}"
PORT="${MEMENTO_ACP_PORT:-47200}"
BASE="http://${HOST}:${PORT}"

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // ""')

# Safety: block dangerous shell patterns
if [ "$TOOL_NAME" = "bash" ] || [ "$TOOL_NAME" = "shell" ] || [ "$TOOL_NAME" = "execute_bash" ]; then
  case "$TOOL_INPUT" in
    *"rm -rf /"*|*"mkfs."*|*":(){"*|*"dd if="*"of=/dev/"*)
      echo "[memento] Blocked dangerous command."
      exit 2
      ;;
  esac
fi

# Discover relevant skills
QUERY=$(echo "$INPUT" | jq -r '"\(.tool_name // "") \(.tool_input // "")"')
result=$(curl -sf --max-time 5 -X POST "${BASE}/discover" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg query "$QUERY" --argjson k 3 '{query: $query, k: $k}')" 2>/dev/null || true)

if [ -n "$result" ] && echo "$result" | jq -e '.skills | length > 0' >/dev/null 2>&1; then
  echo "[memento] Relevant skills for ${TOOL_NAME}:"
  echo "$result" | jq -r '.skills[] | "  - \(.name): \(.description // "no description")"'
fi

exit 0
