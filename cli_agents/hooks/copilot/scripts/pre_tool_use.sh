#!/bin/bash
# Memento-Skills: Pre-Tool-Use Hook for GitHub Copilot CLI
# Input (JSON via stdin): { "timestamp": ..., "cwd": "...", "toolName": "...", "toolArgs": "{...}" }
# Output (JSON to stdout): optional context injection or deny decision
set -e

INPUT=$(cat)
MEMENTO_URL="http://${MEMENTO_ACP_HOST:-127.0.0.1}:${MEMENTO_ACP_PORT:-47200}"

TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // ""')
TOOL_ARGS=$(echo "$INPUT" | jq -r '.toolArgs // "{}"')

# ---- 1. Skip read-only tools ----
case "$TOOL_NAME" in
    view|read_file|list_dir)
        exit 0
        ;;
esac

# ---- 2. Safety check for bash commands ----
if [ "$TOOL_NAME" = "bash" ]; then
    COMMAND=$(echo "$TOOL_ARGS" | jq -r '.command // ""' 2>/dev/null || echo "")
    if echo "$COMMAND" | grep -qE '(sudo\s+)?rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)*-*r[a-zA-Z]*\s+/([^/]|$)|(sudo\s+)?rm\s+.*--no-preserve-root|mkfs|dd\s+if=|:()\{\s*:\||\|\s*:\s*\}|format\s+[A-Z]:'; then
        jq -n '{permissionDecision: "deny", permissionDecisionReason: "Memento safety policy: Potentially destructive system command detected"}' 
        exit 0
    fi
fi

# ---- 3. Discover relevant skills ----
DESCRIPTION=$(echo "$TOOL_ARGS" | jq -r '.description // ""' 2>/dev/null || echo "")
COMMAND=$(echo "$TOOL_ARGS" | jq -r '.command // ""' 2>/dev/null || echo "")
QUERY="${DESCRIPTION:-${COMMAND:-${TOOL_NAME}}}"

DISCOVER_RESULT=$(curl -s --max-time 5 -X POST "${MEMENTO_URL}/discover" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg q "$QUERY" --arg t "$TOOL_NAME" '{query: $q, tool_name: $t, k: 3}')" \
    2>/dev/null || echo '{"skills":[]}')

# ---- 4. Inject discovered skills into agent context via stdout ----
SKILL_COUNT=$(echo "$DISCOVER_RESULT" | jq '.skills | length' 2>/dev/null || echo "0")

if [ "$SKILL_COUNT" -gt 0 ]; then
    SKILL_CONTEXT=$(echo "$DISCOVER_RESULT" | jq -r '[.skills[] | "- \(.name): \(.description // "no description")"] | join("\n")' 2>/dev/null || echo "")
    if [ -n "$SKILL_CONTEXT" ]; then
        jq -n --arg ctx "Memento skills available for this task:\n${SKILL_CONTEXT}" '{additionalContext: $ctx}'
        echo "[memento] Injected ${SKILL_COUNT} skill(s) into context" >&2
    fi
fi

exit 0
