"""Integration test: deploy Kiro hooks to an external project and verify."""

import json
import os
import subprocess
from pathlib import Path

import pytest

COGNEE_DIR = Path("/home/philipp/github/cognee")

pytestmark = pytest.mark.skipif(
    not COGNEE_DIR.exists(), reason="cognee project not available"
)


@pytest.fixture(autouse=True)
def _setup_sys_path():
    import sys
    root = str(Path(__file__).resolve().parent.parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)


@pytest.fixture()
def deployed(tmp_path):
    """Deploy hooks to a temp copy to avoid polluting cognee."""
    from cli_agents.adapters.copilot_cli import KiroAdapter

    ws = tmp_path / "project"
    ws.mkdir()
    adapter = KiroAdapter(ws)
    adapter.generate_hooks()
    return ws, adapter


# ── File structure ──────────────────────────────────────────────


class TestFileStructure:
    def test_agent_config_exists(self, deployed):
        ws, _ = deployed
        assert (ws / ".kiro" / "agents" / "memento.json").exists()

    def test_agent_config_valid_json(self, deployed):
        ws, _ = deployed
        data = json.loads((ws / ".kiro" / "agents" / "memento.json").read_text())
        assert data["name"] == "memento"
        assert set(data["hooks"]) == {"agentSpawn", "preToolUse", "postToolUse", "stop"}

    def test_four_scripts_created(self, deployed):
        ws, _ = deployed
        scripts = list((ws / ".kiro" / "hooks" / "scripts").glob("*.sh"))
        assert len(scripts) == 4

    def test_scripts_executable(self, deployed):
        ws, _ = deployed
        for sh in (ws / ".kiro" / "hooks" / "scripts").glob("*.sh"):
            assert os.access(sh, os.X_OK), f"{sh.name} not executable"

    def test_scripts_valid_bash(self, deployed):
        ws, _ = deployed
        for sh in (ws / ".kiro" / "hooks" / "scripts").glob("*.sh"):
            r = subprocess.run(["bash", "-n", str(sh)], capture_output=True)
            assert r.returncode == 0, f"{sh.name} syntax error: {r.stderr.decode()}"

    def test_verify_reports_installed(self, deployed):
        _, adapter = deployed
        v = adapter.verify()
        assert v["hooks_installed"] is True
        assert v["scripts_count"] == 4
        assert v["scripts_executable"] is True


# ── Hook behaviour ──────────────────────────────────────────────


def _run_hook(ws: Path, script: str, stdin_json: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(ws / ".kiro" / "hooks" / "scripts" / script)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        timeout=10,
    )


class TestPreToolUse:
    def test_safe_tool_exits_0(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "pre_tool_use.sh", {
            "hook_event_name": "preToolUse", "cwd": "/tmp",
            "tool_name": "fs_read", "tool_input": {"path": "/tmp/x"},
        })
        assert r.returncode == 0

    def test_dangerous_execute_bash_exits_2(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "pre_tool_use.sh", {
            "hook_event_name": "preToolUse", "cwd": "/tmp",
            "tool_name": "execute_bash",
            "tool_input": {"command": "rm -rf /home"},
        })
        assert r.returncode == 2

    def test_dangerous_bash_exits_2(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "pre_tool_use.sh", {
            "hook_event_name": "preToolUse", "cwd": "/tmp",
            "tool_name": "bash",
            "tool_input": {"command": "rm -rf /"},
        })
        assert r.returncode == 2

    def test_safe_bash_exits_0(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "pre_tool_use.sh", {
            "hook_event_name": "preToolUse", "cwd": "/tmp",
            "tool_name": "execute_bash",
            "tool_input": {"command": "ls -la"},
        })
        assert r.returncode == 0

    def test_mkfs_blocked(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "pre_tool_use.sh", {
            "hook_event_name": "preToolUse", "cwd": "/tmp",
            "tool_name": "bash",
            "tool_input": {"command": "mkfs.ext4 /dev/sda"},
        })
        assert r.returncode == 2

    def test_fork_bomb_blocked(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "pre_tool_use.sh", {
            "hook_event_name": "preToolUse", "cwd": "/tmp",
            "tool_name": "shell",
            "tool_input": {"command": ":(){ :|:& };:"},
        })
        assert r.returncode == 2


class TestPostToolUse:
    def test_success_exits_0(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "post_tool_use.sh", {
            "hook_event_name": "postToolUse", "cwd": "/tmp",
            "tool_name": "fs_read", "tool_input": {},
            "tool_response": {"success": True, "result": ["ok"]},
        })
        assert r.returncode == 0

    def test_failure_exits_0(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "post_tool_use.sh", {
            "hook_event_name": "postToolUse", "cwd": "/tmp",
            "tool_name": "execute_bash", "tool_input": {},
            "tool_response": {"success": False, "result": ["Error: file not found"]},
        })
        assert r.returncode == 0


class TestSessionHooks:
    def test_session_start_exits_0(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "session_start.sh", {
            "hook_event_name": "agentSpawn", "cwd": "/tmp",
        })
        assert r.returncode == 0

    def test_session_end_exits_0(self, deployed):
        ws, _ = deployed
        r = _run_hook(ws, "session_end.sh", {
            "hook_event_name": "stop", "cwd": "/tmp",
            "assistant_response": "Task complete.",
        })
        assert r.returncode == 0


# ── Deploy to cognee (real project) ────────────────────────────


class TestCogneeDeploy:
    def test_deploy_and_verify(self):
        from cli_agents.adapters.copilot_cli import KiroAdapter

        adapter = KiroAdapter(COGNEE_DIR)
        result = adapter.generate_hooks()

        assert "agent_config" in result
        assert len(result["scripts"]) == 4

        config = json.loads(
            (COGNEE_DIR / ".kiro" / "agents" / "memento.json").read_text()
        )
        assert config["name"] == "memento"
        assert "preToolUse" in config["hooks"]

        v = adapter.verify()
        assert v["hooks_installed"] is True
        assert v["scripts_count"] == 4
        assert v["scripts_executable"] is True

    def test_pre_tool_use_blocks_dangerous(self):
        r = _run_hook(COGNEE_DIR, "pre_tool_use.sh", {
            "hook_event_name": "preToolUse", "cwd": str(COGNEE_DIR),
            "tool_name": "execute_bash",
            "tool_input": {"command": "rm -rf /"},
        })
        assert r.returncode == 2

    def test_pre_tool_use_allows_safe(self):
        r = _run_hook(COGNEE_DIR, "pre_tool_use.sh", {
            "hook_event_name": "preToolUse", "cwd": str(COGNEE_DIR),
            "tool_name": "fs_read",
            "tool_input": {"path": str(COGNEE_DIR / "README.md")},
        })
        assert r.returncode == 0
