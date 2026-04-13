"""Automated bootstrap for CLI agent integration.

This module handles the complete setup process for integrating
Memento-Skills with a CLI coding agent. It:

1. Detects the target CLI agent (or accepts explicit target)
2. Generates and installs hook configurations
3. Converts Memento skills to the target format
4. Starts the ACP wrapper server
5. Verifies the integration
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import stat
from pathlib import Path
from typing import Any

from cli_agents.auto.detector import detect_cli_agent
from cli_agents.config import AdapterConfig, ACPServerConfig

logger = logging.getLogger("memento.bootstrap")


class CLIAgentBootstrap:
    """Orchestrate the full setup of CLI agent integration."""

    def __init__(
        self,
        target: str | None = None,
        workspace: Path | None = None,
        config: AdapterConfig | None = None,
    ):
        self.workspace = workspace or Path.cwd()
        self.config = config or AdapterConfig()

        if target:
            self.config.target = target
        elif not target:
            # Auto-detect
            detection = detect_cli_agent(self.workspace)
            if detection.is_detected:
                self.config.target = detection.agent
                logger.info(
                    "Auto-detected CLI agent: %s (confidence: %.0f%%)",
                    detection.agent,
                    detection.confidence * 100,
                )

    def setup(self) -> dict[str, Any]:
        """Run the complete setup process.

        Returns:
            Dictionary with setup results and status for each step.
        """
        results: dict[str, Any] = {
            "target": self.config.target,
            "workspace": str(self.workspace),
            "steps": {},
        }

        # Step 1: Install hooks
        try:
            hooks_result = self._install_hooks()
            results["steps"]["hooks"] = {"status": "ok", **hooks_result}
        except Exception as exc:
            logger.exception("Failed to install hooks")
            results["steps"]["hooks"] = {"status": "error", "error": str(exc)}

        # Step 2: Convert and install skills
        try:
            skills_result = self._install_skills()
            results["steps"]["skills"] = {"status": "ok", **skills_result}
        except Exception as exc:
            logger.exception("Failed to install skills")
            results["steps"]["skills"] = {"status": "error", "error": str(exc)}

        # Step 3: Save configuration
        try:
            self.config.workspace_dir = self.workspace
            self.config.save()
            results["steps"]["config"] = {"status": "ok"}
        except Exception as exc:
            logger.exception("Failed to save config")
            results["steps"]["config"] = {"status": "error", "error": str(exc)}

        # Step 4: Verify connectivity (optional)
        try:
            verify_result = self._verify()
            results["steps"]["verify"] = {"status": "ok", **verify_result}
        except Exception as exc:
            results["steps"]["verify"] = {"status": "skipped", "reason": str(exc)}

        # Overall status
        results["success"] = all(
            step.get("status") == "ok"
            for key, step in results["steps"].items()
            if key != "verify"  # Verify is optional
        )

        return results

    def _install_hooks(self) -> dict:
        """Install hook configurations for the target platform."""
        hooks_source = Path(__file__).parent.parent / "hooks"

        if self.config.target == "copilot-cli":
            return self._install_copilot_hooks(hooks_source / "copilot")
        elif self.config.target == "kiro":
            return self._install_kiro_hooks(hooks_source / "kiro")
        else:
            raise ValueError(f"Unknown target: {self.config.target}")

    def _install_copilot_hooks(self, source: Path) -> dict:
        """Install GitHub Copilot CLI hooks."""
        hooks_dest = self.workspace / ".github" / "hooks"
        hooks_dest.mkdir(parents=True, exist_ok=True)

        # Copy hooks.json
        hooks_json = source / "hooks.json"
        if hooks_json.exists():
            dest_json = hooks_dest / "memento-hooks.json"
            shutil.copy2(hooks_json, dest_json)

        # Copy and make scripts executable
        scripts_src = source / "scripts"
        scripts_dest = hooks_dest / "scripts"
        scripts_dest.mkdir(parents=True, exist_ok=True)

        copied_scripts = []
        if scripts_src.exists():
            for script in scripts_src.glob("*.sh"):
                dest_script = scripts_dest / script.name
                shutil.copy2(script, dest_script)
                # Make executable
                dest_script.chmod(
                    dest_script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
                )
                copied_scripts.append(script.name)

        return {
            "hooks_dir": str(hooks_dest),
            "hooks_config": str(hooks_dest / "memento-hooks.json"),
            "scripts": copied_scripts,
        }

    def _install_kiro_hooks(self, source: Path) -> dict:
        """Install Kiro hooks."""
        hooks_dest = self.workspace / ".kiro" / "hooks"
        hooks_dest.mkdir(parents=True, exist_ok=True)

        copied_hooks = []
        for hook_file in source.glob("*.yaml"):
            dest_hook = hooks_dest / hook_file.name
            shutil.copy2(hook_file, dest_hook)
            copied_hooks.append(hook_file.name)

        return {
            "hooks_dir": str(hooks_dest),
            "hooks": copied_hooks,
        }

    def _install_skills(self) -> dict:
        """Convert and install Memento skills."""
        from cli_agents.skills.converter import SkillConverter

        # Find Memento's builtin skills
        builtin_skills = Path(__file__).parent.parent.parent / "builtin" / "skills"
        user_skills = self.config.skills_dir

        # Use builtin skills as source (always available)
        source_dir = builtin_skills if builtin_skills.exists() else user_skills

        converter = SkillConverter(
            source_dir=source_dir,
            target=self.config.target,
            workspace=self.workspace,
        )

        # Run synchronously (wrap async)
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    count, output_dir = pool.submit(
                        lambda: asyncio.run(converter.sync_all())
                    ).result()
            else:
                count, output_dir = loop.run_until_complete(converter.sync_all())
        except RuntimeError:
            count, output_dir = asyncio.run(converter.sync_all())

        return {
            "skills_synced": count,
            "source_dir": str(source_dir),
            "output_dir": str(output_dir),
        }

    def _verify(self) -> dict:
        """Verify the integration is working."""
        from cli_agents.wrapper.acp_client import ACPClient

        client = ACPClient(
            base_url=self.config.server.base_url,
            timeout=5,
        )

        server_running = client.is_available()
        return {
            "server_running": server_running,
            "server_url": self.config.server.base_url,
        }


def run_bootstrap(
    target: str | None = None,
    workspace: str | None = None,
    auto: bool = False,
) -> dict:
    """Entry point for the bootstrap process.

    Args:
        target: Target platform ("copilot-cli" or "kiro"). Auto-detected if None.
        workspace: Workspace directory. Defaults to cwd.
        auto: If True, auto-detect everything and proceed without prompting.

    Returns:
        Setup results dictionary.
    """
    ws = Path(workspace) if workspace else Path.cwd()

    bootstrap = CLIAgentBootstrap(target=target, workspace=ws)
    results = bootstrap.setup()

    return results
