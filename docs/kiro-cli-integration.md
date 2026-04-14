# Kiro CLI Integration — Memento-Skills

Integrate Memento-Skills' self-evolving skill system into any project using Kiro CLI.
The integration uses Kiro's agent hooks to discover skills before tool calls,
record outcomes for reflective learning, and block dangerous commands.

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| Kiro CLI (`kiro-cli`) | The host agent that runs hooks |
| `jq` | JSON processing in hook scripts |
| `curl` | HTTP calls to the ACP server |
| Memento-Skills (optional) | ACP server for full skill discovery/learning |

The hooks degrade gracefully — if the ACP server isn't running, hooks exit cleanly
and Kiro continues normally.

## Quick Setup

### Option A: Automated (requires Memento-Skills installed)

```bash
cd /path/to/your-project
memento adapt --target kiro
memento serve --daemon          # optional: start the ACP server
memento adapt --verify          # verify the integration
```

### Option B: Programmatic

```python
from pathlib import Path
from cli_agents.adapters.copilot_cli import KiroAdapter

adapter = KiroAdapter(Path("/path/to/your-project"))
adapter.generate_hooks()        # creates .kiro/agents/ and .kiro/hooks/scripts/
print(adapter.verify())         # check everything is in place
```

### Option C: Manual

Copy these files into your project:

```
your-project/
├── .kiro/
│   ├── agents/
│   │   └── memento.json              # agent config with hook definitions
│   └── hooks/
│       └── scripts/
│           ├── session_start.sh       # agentSpawn hook
│           ├── pre_tool_use.sh        # preToolUse hook
│           ├── post_tool_use.sh       # postToolUse hook
│           └── session_end.sh         # stop hook
```

Make scripts executable: `chmod +x .kiro/hooks/scripts/*.sh`

## What Gets Created

### `.kiro/agents/memento.json`

This is a standard Kiro agent configuration. Kiro loads it when you switch to the
`memento` agent via `/agent memento`, or you can merge the hooks into your existing
agent config.

```json
{
  "name": "memento",
  "description": "Memento-Skills integration — self-evolving skill discovery and reflective learning",
  "hooks": {
    "agentSpawn":  [{"command": ".kiro/hooks/scripts/session_start.sh", "description": "Start ACP server and sync skills"}],
    "preToolUse":  [{"command": ".kiro/hooks/scripts/pre_tool_use.sh",  "description": "Discover relevant Memento skills"}],
    "postToolUse": [{"command": ".kiro/hooks/scripts/post_tool_use.sh", "description": "Record outcome for reflective learning"}],
    "stop":        [{"command": ".kiro/hooks/scripts/session_end.sh",   "description": "Persist learning data"}]
  }
}
```

### Hook Scripts

All scripts read JSON from STDIN (Kiro's hook protocol) and use `jq` for safe
JSON handling — no shell string interpolation into JSON payloads.

| Script | Trigger | What It Does |
|--------|---------|-------------|
| `session_start.sh` | `agentSpawn` | Checks ACP server health, syncs skills to Kiro format |
| `pre_tool_use.sh` | `preToolUse` | Blocks dangerous shell commands (exit 2), discovers relevant skills and outputs them to STDOUT (added to agent context) |
| `post_tool_use.sh` | `postToolUse` | Classifies tool result as success/failure, records outcome via ACP `/reflect` |
| `session_end.sh` | `stop` | Records session end for learning persistence |

## How Kiro Hooks Work

Kiro hooks are defined in agent JSON configs at `.kiro/agents/*.json`. Each hook:

1. Receives a JSON event on **STDIN** with fields like `hook_event_name`, `cwd`,
   `tool_name`, `tool_input`, `tool_response`
2. Runs a shell command
3. Uses **exit codes** to signal results:
   - `0` — success; STDOUT is added to agent context (for `agentSpawn`, `preToolUse`)
   - `2` — block tool execution (only `preToolUse`); STDERR returned to the LLM
   - other — warning shown to user

## Hook Lifecycle

```
User starts Kiro session
    │
    ├── agentSpawn ──→ session_start.sh
    │                   • Check ACP server health
    │                   • Sync skills to Kiro format
    │
    ├── User sends prompt
    │
    ├── preToolUse ──→ pre_tool_use.sh (for each tool call)
    │                   • Safety gate: block rm -rf /, mkfs, fork bombs
    │                   • Discover relevant skills via ACP /discover
    │                   • Output skill context to STDOUT → agent context
    │
    ├── (tool executes)
    │
    ├── postToolUse ──→ post_tool_use.sh
    │                   • Classify result as success/failure
    │                   • Record outcome via ACP /reflect
    │
    ├── (assistant responds)
    │
    └── stop ──→ session_end.sh
                    • Record session end
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMENTO_ACP_HOST` | `127.0.0.1` | ACP server host |
| `MEMENTO_ACP_PORT` | `47200` | ACP server port |

Set these in your shell profile or in the agent config's hook environment if you
run the ACP server on a non-default address.

### ACP Server (Optional)

The ACP server provides skill discovery, execution, and reflective learning.
Without it, hooks still provide the safety gate but skip skill discovery.

```bash
memento serve --daemon           # start in background
memento serve --status           # check if running
memento serve --stop             # stop the daemon
```

### Adding Hooks to an Existing Agent

If you already have a Kiro agent config, merge the hooks section:

```json
{
  "name": "my-existing-agent",
  "hooks": {
    "preToolUse": [
      {"command": ".kiro/hooks/scripts/pre_tool_use.sh", "description": "Memento skill discovery"}
    ],
    "postToolUse": [
      {"command": ".kiro/hooks/scripts/post_tool_use.sh", "description": "Memento reflection"}
    ]
  }
}
```

You can pick only the hooks you want — they're independent.

## Safety Gate

The `preToolUse` hook blocks dangerous shell commands by exiting with code 2.
Blocked patterns (for tools named `bash`, `shell`, or `execute_bash`):

| Pattern | Example |
|---------|---------|
| `rm -rf /...` | `rm -rf /home` |
| `mkfs.*` | `mkfs.ext4 /dev/sda` |
| Fork bomb | `:(){ :\|:& };:` |
| Raw disk write | `dd if=... of=/dev/...` |

Safe commands like `rm -rf ./build` are not blocked.

## Verification

```bash
# Check files exist and are executable
memento adapt --verify --target kiro

# Or programmatically
python -c "
from pathlib import Path
from cli_agents.adapters.copilot_cli import KiroAdapter
a = KiroAdapter(Path('.'))
print(a.verify())
"
```

Expected output:
```
{'hooks_installed': True, 'scripts_count': 4, 'scripts_executable': True, 'skills_count': 0}
```

## Testing Hooks Manually

```bash
# Safe tool call — should exit 0
echo '{"hook_event_name":"preToolUse","cwd":".","tool_name":"fs_read","tool_input":{}}' \
  | bash .kiro/hooks/scripts/pre_tool_use.sh
echo "Exit: $?"

# Dangerous command — should exit 2
echo '{"hook_event_name":"preToolUse","cwd":".","tool_name":"execute_bash","tool_input":{"command":"rm -rf /"}}' \
  | bash .kiro/hooks/scripts/pre_tool_use.sh
echo "Exit: $?"

# Post-tool recording — should exit 0
echo '{"hook_event_name":"postToolUse","cwd":".","tool_name":"fs_write","tool_input":{},"tool_response":{"success":true}}' \
  | bash .kiro/hooks/scripts/post_tool_use.sh
echo "Exit: $?"
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Hooks not running | Check you're using the `memento` agent: `/agent memento` |
| "No hooks configured" | Verify `.kiro/agents/memento.json` exists and is valid JSON |
| Scripts not executable | Run `chmod +x .kiro/hooks/scripts/*.sh` |
| `jq: command not found` | Install jq: `apt install jq` / `brew install jq` |
| Skills not discovered | Start the ACP server: `memento serve --daemon` |
| ACP server won't start | Check port 47200 isn't in use: `lsof -i :47200` |
