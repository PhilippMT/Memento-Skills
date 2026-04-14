"""Tests for cli_agents.auto.detector."""

import pytest
from pathlib import Path

from cli_agents.auto.detector import (
    DetectionResult,
    detect_cli_agent,
    _detect_kiro,
    _detect_copilot_cli,
)


# --- DetectionResult.is_detected ---

def test_is_detected_true():
    assert DetectionResult(agent="kiro", confidence=0.5, details={}).is_detected is True

def test_is_detected_false():
    assert DetectionResult(agent="unknown", confidence=0.0, details={}).is_detected is False


# --- _detect_kiro ---

def test_kiro_with_kiro_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    (tmp_path / ".kiro").mkdir()
    r = _detect_kiro(tmp_path)
    assert r.agent == "kiro"
    assert r.confidence == pytest.approx(0.4)

def test_kiro_with_kiro_and_agents(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    (tmp_path / ".kiro" / "agents").mkdir(parents=True)
    r = _detect_kiro(tmp_path)
    assert r.agent == "kiro"
    assert r.confidence == pytest.approx(0.7)

def test_kiro_full_score(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    for sub in ("agents", "hooks", "steering"):
        (tmp_path / ".kiro" / sub).mkdir(parents=True, exist_ok=True)
    r = _detect_kiro(tmp_path)
    assert r.agent == "kiro"
    assert r.confidence == pytest.approx(1.0)

def test_kiro_empty_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    r = _detect_kiro(tmp_path)
    assert r.agent == "unknown"


# --- _detect_copilot_cli ---

def test_copilot_with_hooks(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.delenv("GITHUB_COPILOT_SESSION", raising=False)
    monkeypatch.delenv("COPILOT_AGENT_SESSION", raising=False)
    monkeypatch.delenv("GH_COPILOT", raising=False)
    (tmp_path / ".github" / "hooks").mkdir(parents=True)
    r = _detect_copilot_cli(tmp_path)
    assert r.agent == "copilot-cli"
    assert r.confidence == pytest.approx(0.2)

def test_copilot_empty_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.delenv("GITHUB_COPILOT_SESSION", raising=False)
    monkeypatch.delenv("COPILOT_AGENT_SESSION", raising=False)
    monkeypatch.delenv("GH_COPILOT", raising=False)
    r = _detect_copilot_cli(tmp_path)
    assert r.agent == "unknown"


# --- detect_cli_agent ---

def test_detect_cli_agent_returns_highest(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.delenv("GITHUB_COPILOT_SESSION", raising=False)
    monkeypatch.delenv("COPILOT_AGENT_SESSION", raising=False)
    monkeypatch.delenv("GH_COPILOT", raising=False)
    # kiro signals: .kiro + .kiro/agents = 0.7
    (tmp_path / ".kiro" / "agents").mkdir(parents=True)
    # copilot signal: .github/hooks = 0.2
    (tmp_path / ".github" / "hooks").mkdir(parents=True)
    r = detect_cli_agent(tmp_path)
    assert r.agent == "kiro"
    assert r.confidence > 0.2


# --- env vars NOT checked for kiro ---

def test_kiro_ignores_env_vars(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setenv("KIRO_SESSION", "fake")
    monkeypatch.setenv("KIRO_WORKSPACE", "/fake")
    r = _detect_kiro(tmp_path)
    # No filesystem signals -> still unknown despite env vars
    assert r.agent == "unknown"
    assert r.confidence == 0.0
