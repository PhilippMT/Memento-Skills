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

import logging
from pathlib import Path
from typing import Any

from cli_agents.auto.detector import detect_cli_agent
from cli_agents.config import AdapterConfig

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
        from cli_agents.adapters.copilot_cli import get_adapter
        adapter = get_adapter(self.config.target, self.workspace)
        return adapter.generate_hooks(self.config.server.base_url)

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

        # Run synchronously
        count, output_dir = converter.sync_all()

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
) -> dict:
    """Entry point for the bootstrap process.

    Args:
        target: Target platform ("copilot-cli" or "kiro"). Auto-detected if None.
        workspace: Workspace directory. Defaults to cwd.

    Returns:
        Setup results dictionary.
    """
    ws = Path(workspace) if workspace else Path.cwd()

    bootstrap = CLIAgentBootstrap(target=target, workspace=ws)
    results = bootstrap.setup()

    return results
