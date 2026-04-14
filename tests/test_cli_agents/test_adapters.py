"""Tests for cli_agents.adapters.copilot_cli."""

import json

import pytest

from cli_agents.adapters.copilot_cli import (
    CopilotCLIAdapter,
    KiroAdapter,
    _parse_url,
    get_adapter,
)


# ---------------------------------------------------------------------------
# CopilotCLIAdapter
# ---------------------------------------------------------------------------


class TestCopilotCLIAdapter:
    def test_platform_name(self, tmp_path):
        assert CopilotCLIAdapter(tmp_path).platform_name() == "copilot-cli"

    def test_hooks_dir(self, tmp_path):
        assert CopilotCLIAdapter(tmp_path).hooks_dir() == tmp_path / ".github" / "hooks"

    def test_skills_dir(self, tmp_path):
        assert CopilotCLIAdapter(tmp_path).skills_dir() == tmp_path / ".github" / "skills"

    def test_generate_hooks_structure(self, tmp_path):
        result = CopilotCLIAdapter(tmp_path).generate_hooks()

        hooks_path = tmp_path / ".github" / "hooks" / "memento-hooks.json"
        assert hooks_path.exists()
        config = json.loads(hooks_path.read_text())

        assert config["version"] == 1
        assert set(config["hooks"].keys()) == {
            "sessionStart",
            "preToolUse",
            "postToolUse",
            "sessionEnd",
            "errorOccurred",
        }
        # No powershell fields anywhere
        raw = hooks_path.read_text()
        assert "powershell" not in raw

        # Scripts were copied from bundled dir
        assert len(result["scripts"]) > 0

    def test_convert_skill(self, tmp_path):
        md = CopilotCLIAdapter(tmp_path).convert_skill(
            name="test-skill",
            description="A test",
            metadata={"dependencies": ["requests"]},
            body="Do stuff.",
        )
        assert md.startswith("---")
        assert "name: test-skill" in md
        assert 'description: "A test"' in md
        assert "source: memento-skills" in md
        assert "- requests" in md
        assert "Do stuff." in md

    def test_verify_hooks_not_installed(self, tmp_path):
        result = CopilotCLIAdapter(tmp_path).verify()
        assert result["hooks_installed"] is False
        assert result["scripts_count"] == 0
        assert result["scripts_executable"] is False
        assert result["skills_count"] == 0


# ---------------------------------------------------------------------------
# KiroAdapter
# ---------------------------------------------------------------------------


class TestKiroAdapter:
    def test_platform_name(self, tmp_path):
        assert KiroAdapter(tmp_path).platform_name() == "kiro"

    def test_hooks_dir(self, tmp_path):
        assert KiroAdapter(tmp_path).hooks_dir() == tmp_path / ".kiro" / "hooks" / "scripts"

    def test_skills_dir(self, tmp_path):
        assert KiroAdapter(tmp_path).skills_dir() == tmp_path / ".kiro" / "skills"

    def test_generate_hooks(self, tmp_path):
        result = KiroAdapter(tmp_path).generate_hooks()

        agent_cfg = tmp_path / ".kiro" / "agents" / "memento.json"
        assert agent_cfg.exists()
        data = json.loads(agent_cfg.read_text())
        assert data["name"] == "memento"

        assert len(result["scripts"]) > 0
        scripts_dir = tmp_path / ".kiro" / "hooks" / "scripts"
        for name in result["scripts"]:
            assert (scripts_dir / name).exists()

    def test_convert_skill(self, tmp_path):
        md = KiroAdapter(tmp_path).convert_skill(
            name="my-skill",
            description="Desc",
            metadata={},
            body="Body text.",
        )
        assert "name: my-skill" in md
        assert 'description: "Desc"' in md
        assert "source: memento-skills" in md
        assert "Body text." in md

    def test_verify(self, tmp_path):
        result = KiroAdapter(tmp_path).verify()
        assert result["hooks_installed"] is False
        assert result["scripts_count"] == 0


# ---------------------------------------------------------------------------
# Factory & helpers
# ---------------------------------------------------------------------------


class TestFactory:
    def test_get_adapter_copilot(self, tmp_path):
        assert isinstance(get_adapter("copilot-cli", tmp_path), CopilotCLIAdapter)

    def test_get_adapter_kiro(self, tmp_path):
        assert isinstance(get_adapter("kiro", tmp_path), KiroAdapter)

    def test_get_adapter_invalid(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown target"):
            get_adapter("invalid", tmp_path)


class TestParseUrl:
    def test_default(self):
        assert _parse_url("http://127.0.0.1:47200") == ("127.0.0.1", 47200)

    def test_custom(self):
        assert _parse_url("http://myhost:9999") == ("myhost", 9999)

    def test_no_port(self):
        host, port = _parse_url("http://example.com")
        assert host == "example.com"
        assert port == 47200  # default fallback
