"""Tests for cli_agents.wrapper.acp_client."""

from unittest.mock import patch

import pytest

from cli_agents.wrapper.acp_client import (
    ACPClient,
    ExecutionResult,
    ReflectionResult,
    SkillMatch,
)


class TestACPClientDefaults:
    def test_default_base_url(self):
        assert ACPClient().base_url == "http://127.0.0.1:47200"

    def test_custom_url(self):
        assert ACPClient("http://host:9000").base_url == "http://host:9000"


class TestIsAvailable:
    def test_returns_false_on_connection_error(self):
        client = ACPClient()
        with patch.object(client, "_request_httpx", side_effect=ConnectionError):
            assert client.is_available() is False


class TestDiscover:
    def test_parses_response(self):
        client = ACPClient()
        fake = {
            "skills": [
                {
                    "name": "fs",
                    "description": "filesystem",
                    "relevance_score": 0.9,
                    "metadata": {"k": "v"},
                }
            ]
        }
        with patch.object(client, "_request_httpx", return_value=fake):
            matches = client.discover(query="read file")
        assert len(matches) == 1
        assert matches[0].name == "fs"
        assert matches[0].relevance_score == 0.9


class TestReflect:
    def test_parses_response(self):
        client = ACPClient()
        fake = {"recorded": True, "skill_score_delta": 0.1, "suggestion": "try X"}
        with patch.object(client, "_request_httpx", return_value=fake):
            r = client.reflect(tool_name="bash", result_type="success")
        assert r.recorded is True
        assert r.skill_score_delta == 0.1
        assert r.suggestion == "try X"


class TestDataclasses:
    def test_skill_match(self):
        s = SkillMatch(name="a", description="b", relevance_score=0.5, metadata={})
        assert s.name == "a"

    def test_execution_result(self):
        e = ExecutionResult(ok=True, output="done", error=None, diagnostics={})
        assert e.ok is True

    def test_reflection_result(self):
        r = ReflectionResult(recorded=True, skill_score_delta=0.0, suggestion=None)
        assert r.recorded is True
