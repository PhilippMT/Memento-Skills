# Memento-Skills Kiro Hooks

This directory contains hook configurations for integrating Memento-Skills
with the Kiro IDE/CLI.

## Structure

Kiro hooks are event-driven automation rules stored in `.kiro/hooks/`.
Each hook YAML file defines a trigger event and the action to execute.

## Installation

```bash
# Auto-install via memento CLI
memento adapt --target kiro

# Or manually copy to your project
cp -r cli_agents/hooks/kiro/hooks/ .kiro/hooks/
```

## Hooks Provided

| Hook | Trigger | Action |
|------|---------|--------|
| `memento-sync.yaml` | File save in skills/ | Sync skills to Kiro format |
| `memento-reflect.yaml` | File save in src/ | Record tool outcomes |
| `memento-discover.yaml` | Manual trigger | Search Memento skills |
