"""Convert Memento-Skills to CLI agent platform-native formats.

Converts Memento SKILL.md files into the format expected by:
- GitHub Copilot CLI (.github/skills/{name}/SKILL.md)
- Kiro IDE/CLI (.kiro/skills/{name}/SKILL.md)

The converter preserves the core skill knowledge while adapting the
metadata and structure to each platform's conventions.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger("memento.skill_converter")


class SkillConverter:
    """Convert Memento skills to target platform format."""

    def __init__(
        self,
        source_dir: Path,
        target: str = "copilot-cli",
        workspace: Path | None = None,
    ):
        self.source_dir = source_dir
        self.target = target
        self.workspace = workspace or Path.cwd()

    @property
    def output_dir(self) -> Path:
        """Get the output directory for the target platform."""
        if self.target == "copilot-cli":
            return self.workspace / ".github" / "skills"
        elif self.target == "kiro":
            return self.workspace / ".kiro" / "skills"
        else:
            raise ValueError(f"Unknown target: {self.target}")

    def sync_all(self) -> tuple[int, Path]:
        """Sync all Memento skills to the target platform.

        Returns:
            Tuple of (number of skills synced, output directory path).
        """
        if not self.source_dir.exists():
            logger.warning("Source skills directory does not exist: %s", self.source_dir)
            return 0, self.output_dir

        output = self.output_dir
        output.mkdir(parents=True, exist_ok=True)

        count = 0
        for skill_path in self.source_dir.iterdir():
            if not skill_path.is_dir():
                continue
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                self._convert_skill(skill_path, output / skill_path.name)
                count += 1
            except Exception:
                logger.exception("Failed to convert skill: %s", skill_path.name)

        # Also generate a memento-bridge meta-skill
        self._generate_bridge_skill(output)
        count += 1

        logger.info("Synced %d skills to %s", count, output)
        return count, output

    def _convert_skill(self, source: Path, dest: Path) -> None:
        """Convert a single Memento skill to target format."""
        dest.mkdir(parents=True, exist_ok=True)

        skill_md = source / "SKILL.md"
        content = skill_md.read_text(errors="replace")

        # Parse frontmatter
        name, description, metadata, body = _parse_skill_md(content)
        if not name:
            name = source.name

        # Generate platform-specific SKILL.md
        if self.target == "copilot-cli":
            converted = self._to_copilot_format(name, description, metadata, body, source)
        elif self.target == "kiro":
            converted = self._to_kiro_format(name, description, metadata, body, source)
        else:
            raise ValueError(f"Unknown target: {self.target}")

        (dest / "SKILL.md").write_text(converted)

        # Copy scripts directory if it exists
        scripts_src = source / "scripts"
        if scripts_src.exists():
            scripts_dest = dest / "scripts"
            if scripts_dest.exists():
                shutil.rmtree(scripts_dest)
            shutil.copytree(scripts_src, scripts_dest)

        # Copy references directory if it exists
        refs_src = source / "references"
        if refs_src.exists():
            refs_dest = dest / "references"
            if refs_dest.exists():
                shutil.rmtree(refs_dest)
            shutil.copytree(refs_src, refs_dest)

    def _to_copilot_format(
        self,
        name: str,
        description: str,
        metadata: dict,
        body: str,
        source: Path,
    ) -> str:
        """Convert to GitHub Copilot CLI SKILL.md format."""
        lines = []

        # Frontmatter — Copilot uses simple YAML frontmatter
        lines.append("---")
        lines.append(f"name: {name}")
        lines.append(f"description: \"{description}\"")
        if metadata.get("dependencies"):
            lines.append("metadata:")
            lines.append("  source: memento-skills")
            deps = metadata["dependencies"]
            if deps:
                lines.append("  dependencies:")
                for dep in deps:
                    lines.append(f"    - {dep}")
        lines.append("---")
        lines.append("")

        # Header
        lines.append(f"# {name}")
        lines.append("")
        lines.append(f"> **Source**: Memento-Skills | **Auto-synced**: Yes")
        lines.append("")

        # Add Memento enhancement note
        lines.append("## Memento Integration")
        lines.append("")
        lines.append(
            "This skill is powered by Memento-Skills. For advanced execution "
            "with reflective learning, use the memento-bridge skill or call "
            "the ACP server directly."
        )
        lines.append("")

        # Original body
        lines.append(body)

        return "\n".join(lines)

    def _to_kiro_format(
        self,
        name: str,
        description: str,
        metadata: dict,
        body: str,
        source: Path,
    ) -> str:
        """Convert to Kiro SKILL.md format."""
        lines = []

        # Frontmatter
        lines.append("---")
        lines.append(f"name: {name}")
        lines.append(f"description: \"{description}\"")
        lines.append("source: memento-skills")
        if metadata.get("dependencies"):
            lines.append("dependencies:")
            for dep in metadata["dependencies"]:
                lines.append(f"  - {dep}")
        lines.append("---")
        lines.append("")

        # Header
        lines.append(f"# {name}")
        lines.append("")

        # Original body
        lines.append(body)

        return "\n".join(lines)

    def _generate_bridge_skill(self, output: Path) -> None:
        """Generate the memento-bridge meta-skill.

        This skill acts as a bridge between the CLI agent and the
        Memento-Skills ACP server, enabling dynamic skill discovery
        and execution at runtime.
        """
        bridge_dir = output / "memento-bridge"
        bridge_dir.mkdir(parents=True, exist_ok=True)

        content = """---
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
curl -s -X POST http://localhost:47200/discover \\
  -H "Content-Type: application/json" \\
  -d '{"query": "parse Excel spreadsheet", "k": 3}'
```

### Execute a Skill
```bash
curl -s -X POST http://localhost:47200/execute \\
  -H "Content-Type: application/json" \\
  -d '{"skill_name": "xlsx", "request": "Read data from report.xlsx"}'
```

### Record Outcome
```bash
curl -s -X POST http://localhost:47200/reflect \\
  -H "Content-Type: application/json" \\
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
"""
        (bridge_dir / "SKILL.md").write_text(content)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_skill_md(content: str) -> tuple[str, str, dict, str]:
    """Parse a Memento SKILL.md file into components.

    Returns:
        Tuple of (name, description, metadata dict, body text).
    """
    name = ""
    description = ""
    metadata: dict[str, Any] = {}
    body = content

    # Extract YAML frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if match:
        frontmatter_text = match.group(1)
        body = match.group(2).strip()

        # Parse YAML manually (avoid pyyaml dependency in converter)
        for line in frontmatter_text.split("\n"):
            line = line.strip()
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip("\"'")
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip("\"'")

        # Extract dependencies
        deps_match = re.search(
            r"dependencies:\s*\n((?:\s+-\s+.+\n?)+)",
            frontmatter_text,
        )
        if deps_match:
            deps_text = deps_match.group(1)
            deps = [
                d.strip().lstrip("- ").strip()
                for d in deps_text.strip().split("\n")
                if d.strip().startswith("-")
            ]
            metadata["dependencies"] = deps

    return name, description, metadata, body
