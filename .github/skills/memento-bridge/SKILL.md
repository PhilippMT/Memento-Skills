---
name: memento-bridge
description: "Bridge to the Memento-Skills self-evolving agent framework. Use this skill when you need to discover, execute, or learn from Memento skills dynamically. This enables reflective learning and skill self-improvement."
metadata:
  source: memento-skills
  type: bridge
---

# Memento-Skills Bridge

## Overview

This skill connects to the **Memento-Skills** ACP server running locally,
enabling dynamic skill discovery, execution, and reflective learning.

## When to Use

- When you need specialized knowledge not available in your current tools
- When you want to search for relevant skills before executing a task
- When you want to record execution outcomes for future improvement
- For complex multi-step tasks that benefit from skill-guided execution

## How It Works

The Memento-Skills ACP server runs on `localhost:47200` and exposes:

- **Discovery**: Search for skills matching your current task
- **Execution**: Run a Memento skill with full ReAct loop
- **Reflection**: Record outcomes for self-improvement

## Usage Examples

### Discover Skills
```bash
curl -s -X POST http://localhost:47200/discover \
  -H "Content-Type: application/json" \
  -d '{"query": "parse Excel spreadsheet", "k": 3}'
```

### Execute a Skill
```bash
curl -s -X POST http://localhost:47200/execute \
  -H "Content-Type: application/json" \
  -d '{"skill_name": "xlsx", "request": "Read data from report.xlsx"}'
```

### Record Outcome
```bash
curl -s -X POST http://localhost:47200/reflect \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "bash", "result_type": "success", "result_text": "Task completed"}'
```

### List All Skills
```bash
curl -s http://localhost:47200/skills
```

## Integration Notes

- The ACP server starts automatically via session hooks
- Skills are synced from Memento's skill library on each session start
- All tool executions are recorded for reflective learning
- Skill utility scores improve over time based on success/failure patterns
