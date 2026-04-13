"""Configuration settings for CLI agent integration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# Default ACP server settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47200
DEFAULT_TIMEOUT_SEC = 30
DEFAULT_PID_FILE = "memento-acp.pid"


@dataclass
class ACPServerConfig:
    """Configuration for the ACP wrapper server."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    timeout_sec: int = DEFAULT_TIMEOUT_SEC
    pid_file: str = DEFAULT_PID_FILE
    auto_start: bool = True

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def pid_path(self) -> Path:
        return _resolve_data_dir() / self.pid_file


@dataclass
class AdapterConfig:
    """Top-level configuration for the CLI agents adapter."""

    target: str = "copilot-cli"  # "copilot-cli" or "kiro"
    server: ACPServerConfig = field(default_factory=ACPServerConfig)
    skills_dir: Path = field(default_factory=lambda: _resolve_skills_dir())
    workspace_dir: Path = field(default_factory=lambda: Path.cwd())
    auto_sync: bool = True
    auto_reflect: bool = True

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "timeout_sec": self.server.timeout_sec,
                "auto_start": self.server.auto_start,
            },
            "skills_dir": str(self.skills_dir),
            "workspace_dir": str(self.workspace_dir),
            "auto_sync": self.auto_sync,
            "auto_reflect": self.auto_reflect,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AdapterConfig:
        server_data = data.get("server", {})
        server = ACPServerConfig(
            host=server_data.get("host", DEFAULT_HOST),
            port=server_data.get("port", DEFAULT_PORT),
            timeout_sec=server_data.get("timeout_sec", DEFAULT_TIMEOUT_SEC),
            auto_start=server_data.get("auto_start", True),
        )
        return cls(
            target=data.get("target", "copilot-cli"),
            server=server,
            skills_dir=Path(data.get("skills_dir", _resolve_skills_dir())),
            workspace_dir=Path(data.get("workspace_dir", Path.cwd())),
            auto_sync=data.get("auto_sync", True),
            auto_reflect=data.get("auto_reflect", True),
        )

    def save(self, path: Path | None = None) -> None:
        """Save configuration to file."""
        if path is None:
            path = _resolve_data_dir() / "cli_agents_config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path | None = None) -> AdapterConfig:
        """Load configuration from file, falling back to defaults."""
        if path is None:
            path = _resolve_data_dir() / "cli_agents_config.json"
        if path.exists():
            data = json.loads(path.read_text())
            return cls.from_dict(data)
        return cls()


def _resolve_data_dir() -> Path:
    """Resolve the Memento data directory."""
    return Path.home() / "memento_s"


def _resolve_skills_dir() -> Path:
    """Resolve the default skills directory."""
    return Path.home() / "memento_s" / "workspace" / "skills"
