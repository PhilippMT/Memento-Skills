# Memento-Skills Kiro Hooks

Kiro hooks integration for Memento-Skills. Hooks are defined inside agent
JSON configuration files at `.kiro/agents/*.json`, **not** as standalone
YAML files.

## How Kiro Hooks Work

- Hook types: `agentSpawn`, `userPromptSubmit`, `preToolUse`, `postToolUse`, `stop`
- Each hook has a `command` (shell script), optional `matcher` (tool filter for pre/postToolUse), and optional `description`
- Hooks receive JSON via **STDIN** with fields: `hook_event_name`, `cwd`, `tool_name`, `tool_input`, `tool_response`
- Exit code `0` = success (STDOUT added to agent context for agentSpawn/userPromptSubmit/preToolUse)
- Exit code `2` = block (preToolUse only — prevents the tool from executing)

## Structure

```
.kiro/
├── agents/
│   └── memento.json          # Agent config with hook definitions
└── hooks/
    └── scripts/
        ├── session_start.sh   # agentSpawn — ACP health check + skill sync
        ├── pre_tool_use.sh    # preToolUse — skill discovery + safety gate
        ├── post_tool_use.sh   # postToolUse — record outcome for reflection
        └── session_end.sh     # stop — persist learning data
```

## Installation

```bash
# Auto-install via memento CLI
memento adapt --target kiro

# Or manually copy
mkdir -p .kiro/agents .kiro/hooks/scripts
cp cli_agents/hooks/kiro/memento-agent.json .kiro/agents/memento.json
cp cli_agents/hooks/kiro/scripts/*.sh .kiro/hooks/scripts/
chmod +x .kiro/hooks/scripts/*.sh
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMENTO_ACP_HOST` | `127.0.0.1` | ACP server host |
| `MEMENTO_ACP_PORT` | `47200` | ACP server port |

## Dependencies

Scripts require `jq` for JSON parsing and `curl` for HTTP requests.
