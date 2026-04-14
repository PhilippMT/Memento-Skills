"""Tests for cli_agents.skills.converter."""

import pytest
from pathlib import Path

from cli_agents.skills.converter import SkillConverter, _parse_skill_md


# ---------------------------------------------------------------------------
# _parse_skill_md
# ---------------------------------------------------------------------------

class TestParseSkillMd:
    def test_valid_frontmatter(self):
        content = "---\nname: filesystem\ndescription: File operations\n---\n\nBody text here."
        name, desc, meta, body = _parse_skill_md(content)
        assert name == "filesystem"
        assert desc == "File operations"
        assert body == "Body text here."

    def test_description_with_colons(self):
        content = '---\nname: test\ndescription: "Use this: when needed"\n---\n\nBody.'
        name, desc, meta, body = _parse_skill_md(content)
        assert desc == "Use this: when needed"

    def test_no_frontmatter(self):
        content = "Just plain markdown content."
        name, desc, meta, body = _parse_skill_md(content)
        assert name == ""
        assert desc == ""
        assert body == content

    def test_no_description_field(self):
        content = "---\nname: only-name\n---\n\nSome body."
        name, desc, meta, body = _parse_skill_md(content)
        assert name == "only-name"
        assert desc == ""

    def test_dependencies_list(self):
        content = "---\nname: pdf\ndescription: PDF ops\ndependencies:\n  - pypdf\n  - pillow\n---\n\nBody."
        name, desc, meta, body = _parse_skill_md(content)
        assert meta["dependencies"] == ["pypdf", "pillow"]


# ---------------------------------------------------------------------------
# SkillConverter
# ---------------------------------------------------------------------------

class TestSkillConverter:
    def _make_skill(self, base: Path, name: str, frontmatter: str = "", body: str = "Body.") -> None:
        d = base / name
        d.mkdir(parents=True)
        content = f"---\n{frontmatter}---\n\n{body}" if frontmatter else body
        (d / "SKILL.md").write_text(content)

    def test_sync_all_count(self, tmp_path):
        src = tmp_path / "skills"
        self._make_skill(src, "alpha", "name: alpha\ndescription: A\n")
        self._make_skill(src, "beta", "name: beta\ndescription: B\n")

        conv = SkillConverter(src, target="kiro", workspace=tmp_path)
        count, out = conv.sync_all()
        assert count == 3  # 2 skills + 1 bridge
        assert (out / "alpha" / "SKILL.md").exists()
        assert (out / "beta" / "SKILL.md").exists()
        assert (out / "memento-bridge" / "SKILL.md").exists()

    def test_sync_all_nonexistent_source(self, tmp_path):
        conv = SkillConverter(tmp_path / "nope", target="kiro", workspace=tmp_path)
        count, out = conv.sync_all()
        assert count == 0

    def test_to_copilot_format(self, tmp_path):
        src = tmp_path / "skills"
        self._make_skill(src, "web", "name: web\ndescription: Search\n", "Search the web.")

        conv = SkillConverter(src, target="copilot-cli", workspace=tmp_path)
        result = conv._to_copilot_format("web", "Search", {}, "Search the web.", src / "web")
        assert "---" in result
        assert 'description: "Search"' in result
        assert "## Memento Integration" in result
        assert "Search the web." in result

    def test_to_kiro_format(self, tmp_path):
        conv = SkillConverter(tmp_path, target="kiro", workspace=tmp_path)
        result = conv._to_kiro_format("fs", "File ops", {"dependencies": ["aiofiles"]}, "Body.", tmp_path)
        assert "source: memento-skills" in result
        assert 'description: "File ops"' in result
        assert "- aiofiles" in result

    def test_generate_bridge_skill(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        conv = SkillConverter(tmp_path, target="kiro", workspace=tmp_path)
        conv._generate_bridge_skill(out)
        bridge_md = out / "memento-bridge" / "SKILL.md"
        assert bridge_md.exists()
        text = bridge_md.read_text()
        assert "name: memento-bridge" in text

    def test_output_dir_copilot(self, tmp_path):
        conv = SkillConverter(tmp_path, target="copilot-cli", workspace=tmp_path)
        assert conv.output_dir == tmp_path / ".github" / "skills"

    def test_output_dir_kiro(self, tmp_path):
        conv = SkillConverter(tmp_path, target="kiro", workspace=tmp_path)
        assert conv.output_dir == tmp_path / ".kiro" / "skills"

    def test_name_fallback_from_directory(self, tmp_path):
        src = tmp_path / "skills"
        self._make_skill(src, "my-tool", "description: No name here\n", "Content.")

        conv = SkillConverter(src, target="kiro", workspace=tmp_path)
        conv.sync_all()
        text = (tmp_path / ".kiro" / "skills" / "my-tool" / "SKILL.md").read_text()
        assert "name: my-tool" in text
