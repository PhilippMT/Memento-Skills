"""Base adapter interface for CLI agent platforms."""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any


class BaseCLIAgentAdapter(abc.ABC):
    """Abstract base class for CLI agent platform adapters.

    Each adapter knows how to:
    - Generate hook configurations for its platform
    - Convert Memento skills to its platform format
    - Verify the integration is working
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace

    @abc.abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier."""
        ...

    @abc.abstractmethod
    def hooks_dir(self) -> Path:
        """Return the hooks directory for this platform."""
        ...

    @abc.abstractmethod
    def skills_dir(self) -> Path:
        """Return the skills directory for this platform."""
        ...

    @abc.abstractmethod
    def generate_hooks(self, server_url: str) -> dict[str, Any]:
        """Generate hook configuration files.

        Returns:
            Dictionary describing what was generated.
        """
        ...

    @abc.abstractmethod
    def convert_skill(
        self,
        name: str,
        description: str,
        metadata: dict,
        body: str,
    ) -> str:
        """Convert a Memento skill to this platform's format.

        Returns:
            The converted SKILL.md content.
        """
        ...

    @abc.abstractmethod
    def verify(self) -> dict[str, Any]:
        """Verify the integration is correctly set up.

        Returns:
            Dictionary with verification results.
        """
        ...
