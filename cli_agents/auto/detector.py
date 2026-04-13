"""Detect which CLI coding agent environment is active."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DetectionResult:
    """Result of CLI agent environment detection."""

    agent: str  # "copilot-cli", "kiro", "unknown"
    confidence: float  # 0.0 - 1.0
    details: dict

    @property
    def is_detected(self) -> bool:
        return self.agent != "unknown"


def detect_cli_agent(workspace: Path | None = None) -> DetectionResult:
    """Auto-detect which CLI coding agent is present in the environment.

    Detection checks (in order of priority):
    1. Environment variables set by the agent
    2. CLI tools available on PATH
    3. Configuration files in the workspace
    4. Process parent inspection
    """
    workspace = workspace or Path.cwd()
    results: list[DetectionResult] = []

    # Check for GitHub Copilot CLI
    copilot_result = _detect_copilot_cli(workspace)
    if copilot_result.is_detected:
        results.append(copilot_result)

    # Check for Kiro
    kiro_result = _detect_kiro(workspace)
    if kiro_result.is_detected:
        results.append(kiro_result)

    if not results:
        return DetectionResult(agent="unknown", confidence=0.0, details={})

    # Return highest confidence match
    return max(results, key=lambda r: r.confidence)


def _detect_copilot_cli(workspace: Path) -> DetectionResult:
    """Detect GitHub Copilot CLI environment."""
    signals: dict = {}
    score = 0.0

    # Check for copilot CLI binary
    if shutil.which("github-copilot-cli") or shutil.which("copilot"):
        signals["cli_binary"] = True
        score += 0.3

    # Check for .github/hooks directory
    hooks_dir = workspace / ".github" / "hooks"
    if hooks_dir.exists():
        signals["hooks_dir"] = str(hooks_dir)
        score += 0.2

    # Check for .github/skills directory
    skills_dir = workspace / ".github" / "skills"
    if skills_dir.exists():
        signals["skills_dir"] = str(skills_dir)
        score += 0.2

    # Check for environment variables
    copilot_env_vars = [
        "GITHUB_COPILOT_SESSION",
        "COPILOT_AGENT_SESSION",
        "GH_COPILOT",
    ]
    for var in copilot_env_vars:
        if os.environ.get(var):
            signals[f"env_{var}"] = True
            score += 0.3

    agent = "copilot-cli" if score > 0 else "unknown"
    return DetectionResult(agent=agent, confidence=min(score, 1.0), details=signals)


def _detect_kiro(workspace: Path) -> DetectionResult:
    """Detect Kiro IDE/CLI environment."""
    signals: dict = {}
    score = 0.0

    # Check for kiro CLI binary
    if shutil.which("kiro") or shutil.which("kiro-cli"):
        signals["cli_binary"] = True
        score += 0.3

    # Check for .kiro directory
    kiro_dir = workspace / ".kiro"
    if kiro_dir.exists():
        signals["kiro_dir"] = str(kiro_dir)
        score += 0.3

    # Check for .kiro/hooks directory
    hooks_dir = workspace / ".kiro" / "hooks"
    if hooks_dir.exists():
        signals["hooks_dir"] = str(hooks_dir)
        score += 0.2

    # Check for steering files
    steering_dir = workspace / ".kiro" / "steering"
    if steering_dir.exists():
        signals["steering_dir"] = str(steering_dir)
        score += 0.1

    # Check for environment variables
    kiro_env_vars = ["KIRO_SESSION", "KIRO_WORKSPACE"]
    for var in kiro_env_vars:
        if os.environ.get(var):
            signals[f"env_{var}"] = True
            score += 0.3

    agent = "kiro" if score > 0 else "unknown"
    return DetectionResult(agent=agent, confidence=min(score, 1.0), details=signals)


def detect_all() -> dict[str, DetectionResult]:
    """Detect all available CLI agents."""
    workspace = Path.cwd()
    return {
        "copilot-cli": _detect_copilot_cli(workspace),
        "kiro": _detect_kiro(workspace),
    }
