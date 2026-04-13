# CLI Agents Adapter — Memento-Skills for Copilot CLI & Kiro

Adapt the **Memento-Skills** self-evolving agent framework to work with
CLI coding agents (GitHub Copilot CLI, Kiro) via hooks, skills, and an
ACP (Agent Connect Protocol) wrapper server.

## Quick Start

```bash
# Install Memento-Skills (if not already installed)
pip install -e .

# Auto-detect and set up for your CLI agent environment
memento adapt --auto

# Or target a specific platform
memento adapt --target copilot-cli   # GitHub Copilot CLI
memento adapt --target kiro          # Kiro IDE/CLI

# Start the ACP wrapper server (background daemon)
memento serve --daemon

# Verify the integration
memento adapt --verify
```

## Architecture

```
CLI Agent (Copilot CLI / Kiro)
    │
    ├── sessionStart hook  ──→  Start ACP server, sync skills
    ├── preToolUse hook    ──→  Discover relevant skills, inject context
    ├── postToolUse hook   ──→  Record outcomes, update skill scores
    └── sessionEnd hook    ──→  Persist learning, cleanup
    │
    ▼
ACP Wrapper Server (localhost:47200)
    │
    ├── GET  /health     → Server status
    ├── POST /discover   → Search skills by query
    ├── POST /execute    → Execute a skill
    ├── POST /reflect    → Record execution outcome
    ├── GET  /skills     → List all skills
    └── POST /sync       → Sync skills to platform format
    │
    ▼
Memento-Skills Core (SkillGateway, SkillExecutor, Reflection)
```

## Components

| Component | Description |
|-----------|-------------|
| `wrapper/acp_server.py` | ACP-compatible REST server exposing Memento capabilities |
| `wrapper/acp_client.py` | Python client for calling the ACP server |
| `hooks/copilot/` | GitHub Copilot CLI hooks configuration and scripts |
| `hooks/kiro/` | Kiro IDE/CLI hooks configuration |
| `skills/converter.py` | Convert Memento skills to platform-native format |
| `auto/bootstrap.py` | Automated setup and configuration |
| `auto/detector.py` | Detect which CLI agent environment is active |
| `config/settings.py` | Configuration management |

## How It Works

1. **Setup**: Run `memento adapt --target copilot-cli` to install hooks
   and convert skills to the target format.

2. **Session Start**: When you start a CLI agent session, the
   `sessionStart` hook ensures the ACP server is running and skills are
   synced.

3. **Tool Interception**: Before each tool call, `preToolUse` searches
   Memento's skill library for relevant expertise and can inject
   context or block dangerous operations.

4. **Learning**: After each tool call, `postToolUse` records the outcome.
   Successful patterns increase skill utility scores; failures trigger
   skill improvement suggestions.

5. **Session End**: Learning is persisted and session metrics are saved.

## Research & Decision Trees

See [research/decision_tree.md](research/decision_tree.md) for the full
research analysis and decision tree documentation.
