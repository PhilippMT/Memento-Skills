"""GitHub Copilot CLI adapter."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

from cli_agents.adapters.base import BaseCLIAgentAdapter


class CopilotCLIAdapter(BaseCLIAgentAdapter):
    """Adapter for GitHub Copilot CLI integration.

    Generates:
    - .github/hooks/memento-hooks.json (hook configuration)
    - .github/hooks/scripts/*.sh (hook scripts)
    - .github/skills/*/SKILL.md (converted skills)
    """

    def platform_name(self) -> str:
        return "copilot-cli"

    def hooks_dir(self) -> Path:
        return self.workspace / ".github" / "hooks"

    def skills_dir(self) -> Path:
        return self.workspace / ".github" / "skills"

    def generate_hooks(self, server_url: str = "http://127.0.0.1:47200") -> dict[str, Any]:
        """Generate Copilot CLI hooks configuration."""
        hooks_dir = self.hooks_dir()
        hooks_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = hooks_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        host, port = _parse_url(server_url)

        # Generate hooks.json
        hooks_config = {
            "version": 1,
            "hooks": {
                "sessionStart": [
                    {
                        "type": "command",
                        "bash": "./scripts/session_start.sh",
                        "cwd": ".github/hooks",
                        "timeoutSec": 15,
                        "env": {
                            "MEMENTO_ACP_HOST": host,
                            "MEMENTO_ACP_PORT": str(port),
                        },
                    }
                ],
                "preToolUse": [
                    {
                        "type": "command",
                        "bash": "./scripts/pre_tool_use.sh",
                        "cwd": ".github/hooks",
                        "timeoutSec": 10,
                        "env": {
                            "MEMENTO_ACP_HOST": host,
                            "MEMENTO_ACP_PORT": str(port),
                        },
                    }
                ],
                "postToolUse": [
                    {
                        "type": "command",
                        "bash": "./scripts/post_tool_use.sh",
                        "cwd": ".github/hooks",
                        "timeoutSec": 10,
                        "env": {
                            "MEMENTO_ACP_HOST": host,
                            "MEMENTO_ACP_PORT": str(port),
                        },
                    }
                ],
                "sessionEnd": [
                    {
                        "type": "command",
                        "bash": "./scripts/session_end.sh",
                        "cwd": ".github/hooks",
                        "timeoutSec": 10,
                        "env": {
                            "MEMENTO_ACP_HOST": host,
                            "MEMENTO_ACP_PORT": str(port),
                        },
                    }
                ],
                "errorOccurred": [
                    {
                        "type": "command",
                        "bash": "./scripts/error_occurred.sh",
                        "cwd": ".github/hooks",
                        "timeoutSec": 5,
                        "env": {
                            "MEMENTO_ACP_HOST": host,
                            "MEMENTO_ACP_PORT": str(port),
                        },
                    }
                ],
            },
        }

        hooks_path = hooks_dir / "memento-hooks.json"
        hooks_path.write_text(json.dumps(hooks_config, indent=2))

        generated_scripts = []
        # Copy bundled scripts
        bundled_scripts = Path(__file__).parent.parent / "hooks" / "copilot" / "scripts"
        if bundled_scripts.exists():
            for script in bundled_scripts.glob("*.sh"):
                dest = scripts_dir / script.name
                dest.write_text(script.read_text())
                dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
                generated_scripts.append(script.name)

        return {
            "hooks_config": str(hooks_path),
            "scripts_dir": str(scripts_dir),
            "scripts": generated_scripts,
        }

    def convert_skill(
        self,
        name: str,
        description: str,
        metadata: dict,
        body: str,
    ) -> str:
        """Convert a Memento skill to Copilot CLI SKILL.md format."""
        lines = [
            "---",
            f"name: {name}",
            f'description: "{description}"',
            "metadata:",
            "  source: memento-skills",
        ]

        deps = metadata.get("dependencies", [])
        if deps:
            lines.append("  dependencies:")
            for dep in deps:
                lines.append(f"    - {dep}")

        lines.extend([
            "---",
            "",
            f"# {name}",
            "",
            "> **Source**: Memento-Skills | **Auto-synced**: Yes",
            "",
            body,
        ])

        return "\n".join(lines)

    def verify(self) -> dict[str, Any]:
        """Verify Copilot CLI integration."""
        results: dict[str, Any] = {}

        # Check hooks
        hooks_path = self.hooks_dir() / "memento-hooks.json"
        results["hooks_installed"] = hooks_path.exists()

        # Check scripts
        scripts_dir = self.hooks_dir() / "scripts"
        if scripts_dir.exists():
            scripts = list(scripts_dir.glob("*.sh"))
            results["scripts_count"] = len(scripts)
            results["scripts_executable"] = all(
                os.access(s, os.X_OK) for s in scripts
            )
        else:
            results["scripts_count"] = 0
            results["scripts_executable"] = False

        # Check skills
        skills_dir = self.skills_dir()
        if skills_dir.exists():
            results["skills_count"] = len(
                [d for d in skills_dir.iterdir() if d.is_dir()]
            )
        else:
            results["skills_count"] = 0

        return results


class KiroAdapter(BaseCLIAgentAdapter):
    """Adapter for Kiro IDE/CLI integration.

    Generates:
    - .kiro/hooks/*.yaml (hook configurations)
    - .kiro/skills/*/SKILL.md (converted skills)
    """

    def platform_name(self) -> str:
        return "kiro"

    def hooks_dir(self) -> Path:
        return self.workspace / ".kiro" / "hooks"

    def skills_dir(self) -> Path:
        return self.workspace / ".kiro" / "skills"

    def generate_hooks(self, server_url: str = "http://127.0.0.1:47200") -> dict[str, Any]:
        """Generate Kiro hooks configuration."""
        hooks_dir = self.hooks_dir()
        hooks_dir.mkdir(parents=True, exist_ok=True)

        generated_hooks = []
        # Copy bundled hook YAMLs
        bundled_hooks = Path(__file__).parent.parent / "hooks" / "kiro"
        if bundled_hooks.exists():
            for hook_file in bundled_hooks.glob("*.yaml"):
                dest = hooks_dir / hook_file.name
                content = hook_file.read_text()
                # Replace server URL if different from default
                content = content.replace(
                    "http://127.0.0.1:47200", server_url
                )
                dest.write_text(content)
                generated_hooks.append(hook_file.name)

        return {
            "hooks_dir": str(hooks_dir),
            "hooks": generated_hooks,
        }

    def convert_skill(
        self,
        name: str,
        description: str,
        metadata: dict,
        body: str,
    ) -> str:
        """Convert a Memento skill to Kiro SKILL.md format."""
        lines = [
            "---",
            f"name: {name}",
            f'description: "{description}"',
            "source: memento-skills",
        ]

        deps = metadata.get("dependencies", [])
        if deps:
            lines.append("dependencies:")
            for dep in deps:
                lines.append(f"  - {dep}")

        lines.extend([
            "---",
            "",
            f"# {name}",
            "",
            body,
        ])

        return "\n".join(lines)

    def verify(self) -> dict[str, Any]:
        """Verify Kiro integration."""
        results: dict[str, Any] = {}

        # Check hooks
        hooks_dir = self.hooks_dir()
        if hooks_dir.exists():
            results["hooks_count"] = len(list(hooks_dir.glob("*.yaml")))
        else:
            results["hooks_count"] = 0

        # Check skills
        skills_dir = self.skills_dir()
        if skills_dir.exists():
            results["skills_count"] = len(
                [d for d in skills_dir.iterdir() if d.is_dir()]
            )
        else:
            results["skills_count"] = 0

        results["hooks_installed"] = results["hooks_count"] > 0

        return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import os


def _parse_url(url: str) -> tuple[str, int]:
    """Parse host and port from a URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 47200
    return host, port


def get_adapter(target: str, workspace: Path) -> BaseCLIAgentAdapter:
    """Factory function to get the right adapter."""
    if target == "copilot-cli":
        return CopilotCLIAdapter(workspace)
    elif target == "kiro":
        return KiroAdapter(workspace)
    else:
        raise ValueError(
            f"Unknown target: {target}. Supported: copilot-cli, kiro"
        )
