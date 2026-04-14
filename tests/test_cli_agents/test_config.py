"""Tests for cli_agents.config."""

import json
import pytest
from pathlib import Path

from cli_agents.config import (
    ACPServerConfig,
    AdapterConfig,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_SEC,
    DEFAULT_PID_FILE,
)


# --- ACPServerConfig ---

def test_acp_defaults():
    c = ACPServerConfig()
    assert c.host == "127.0.0.1"
    assert c.port == 47200
    assert c.timeout_sec == 30
    assert c.pid_file == "memento-acp.pid"
    assert c.auto_start is True

def test_acp_base_url():
    c = ACPServerConfig(host="0.0.0.0", port=9999)
    assert c.base_url == "http://0.0.0.0:9999"

def test_acp_base_url_default():
    assert ACPServerConfig().base_url == "http://127.0.0.1:47200"


# --- AdapterConfig roundtrip ---

def test_to_dict_from_dict_roundtrip():
    cfg = AdapterConfig(target="kiro", auto_sync=False, auto_reflect=False)
    d = cfg.to_dict()
    restored = AdapterConfig.from_dict(d)
    assert restored.target == "kiro"
    assert restored.auto_sync is False
    assert restored.auto_reflect is False
    assert restored.server.host == DEFAULT_HOST
    assert restored.server.port == DEFAULT_PORT


# --- save / load ---

def test_save_and_load(tmp_path):
    path = tmp_path / "cfg.json"
    cfg = AdapterConfig(target="kiro", server=ACPServerConfig(port=8080))
    cfg.save(path)
    loaded = AdapterConfig.load(path)
    assert loaded.target == "kiro"
    assert loaded.server.port == 8080

def test_load_nonexistent_returns_defaults(tmp_path):
    path = tmp_path / "nope.json"
    cfg = AdapterConfig.load(path)
    assert cfg.target == "copilot-cli"
    assert cfg.server.port == DEFAULT_PORT


# --- custom host/port propagation ---

def test_custom_host_port():
    srv = ACPServerConfig(host="10.0.0.1", port=5555)
    cfg = AdapterConfig(server=srv)
    d = cfg.to_dict()
    assert d["server"]["host"] == "10.0.0.1"
    assert d["server"]["port"] == 5555
    restored = AdapterConfig.from_dict(d)
    assert restored.server.base_url == "http://10.0.0.1:5555"
