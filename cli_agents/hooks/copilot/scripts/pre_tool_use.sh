#!/bin/bash
# Memento-Skills: Pre-Tool-Use Hook for GitHub Copilot CLI
#
# This hook runs BEFORE the agent uses any tool. It:
# 1. Searches Memento for relevant skills based on the tool context
# 2. Can deny dangerous operations based on Memento safety policies
# 3. Logs tool usage for reflective learning
#
# Input (JSON via stdin):
#   {
#     "timestamp": ...,
#     "cwd": "...",
#     "toolName": "bash"|"edit"|"view"|...,
#     "toolArgs": "{\"command\":\"...\",\"description\":\"...\"}"
#   }
#
# Output (JSON, optional):
#   { "permissionDecision": "allow"|"deny", "permissionDecisionReason": "..." }
set -e

INPUT=$(cat)
MEMENTO_URL="http://${MEMENTO_ACP_HOST:-127.0.0.1}:${MEMENTO_ACP_PORT:-47200}"

TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // ""')
TOOL_ARGS=$(echo "$INPUT" | jq -r '.toolArgs // "{}"')

# ---- 1. Skip non-actionable tools ----
case "$TOOL_NAME" in
    view|read_file|list_dir)
        # Read-only tools — skip skill discovery, just allow
        exit 0
        ;;
esac

# ---- 2. Discover relevant skills ----
# Build a query from the tool context
DESCRIPTION=$(echo "$TOOL_ARGS" | jq -r '.description // ""' 2>/dev/null || echo "")
COMMAND=$(echo "$TOOL_ARGS" | jq -r '.command // ""' 2>/dev/null || echo "")
QUERY="${DESCRIPTION:-${COMMAND:-${TOOL_NAME}}}"

DISCOVER_RESULT=$(curl -s --max-time 5 -X POST "${MEMENTO_URL}/discover" \
    -H "Content-Type: application/json" \
    -d "{\"query\": $(echo "$QUERY" | jq -Rs .), \"tool_name\": \"${TOOL_NAME}\", \"k\": 3}" \
    2>/dev/null || echo '{"skills":[]}')

# ---- 3. Check for dangerous patterns (safety policy) ----
if [ "$TOOL_NAME" = "bash" ]; then
    # Check for dangerous command patterns
    if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+/[^.]|mkfs|dd\s+if=|:(){ :|format\s+[A-Z]:'; then
        echo '{"permissionDecision":"deny","permissionDecisionReason":"Memento safety policy: Potentially destructive system command detected"}'
        exit 0
    fi
fi

# ---- 4. Log the tool use with discovered skills ----
SKILL_NAMES=$(echo "$DISCOVER_RESULT" | jq -r '.skills[]?.name // empty' 2>/dev/null | head -3 | tr '\n' ',' | sed 's/,$//')

if [ -n "$SKILL_NAMES" ]; then
    echo "[memento] Relevant skills for ${TOOL_NAME}: ${SKILL_NAMES}" >&2
fi

# Allow by default
exit 0
