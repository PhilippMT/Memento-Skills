"""ACP Client — Call the Memento ACP wrapper server from hook scripts.

This client provides a simple, synchronous interface for calling the
ACP wrapper server. It is designed to be used from hook scripts that
need to communicate with Memento-Skills at each lifecycle event.

Usage:
    from cli_agents.wrapper.acp_client import ACPClient

    client = ACPClient()  # defaults to localhost:47200

    # Discover relevant skills
    skills = client.discover(query="parse JSON file", tool_name="bash")

    # Execute a skill
    result = client.execute("filesystem", request="read config.json")

    # Record outcome for reflective learning
    client.reflect(
        skill_name="filesystem",
        tool_name="bash",
        result_type="success",
        result_text="File read successfully"
    )
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("memento.acp_client")

DEFAULT_BASE_URL = "http://127.0.0.1:47200"
DEFAULT_TIMEOUT = 10


@dataclass
class SkillMatch:
    """A skill returned from discovery."""

    name: str
    description: str
    relevance_score: float
    metadata: dict


@dataclass
class ExecutionResult:
    """Result from skill execution."""

    ok: bool
    output: str
    error: str | None
    diagnostics: dict


@dataclass
class ReflectionResult:
    """Result from recording a reflection."""

    recorded: bool
    skill_score_delta: float
    suggestion: str | None


class ACPClient:
    """Synchronous client for the Memento ACP wrapper server.

    Uses httpx if available, falls back to urllib for zero-dependency
    operation in hook scripts.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict:
        """Check server health."""
        return self._get("/health")

    def is_available(self) -> bool:
        """Check if the server is reachable."""
        try:
            result = self.health()
            return result.get("status") == "ok"
        except Exception:
            return False

    def ensure_server(self) -> bool:
        """Ensure the ACP server is running, starting it if needed."""
        if self.is_available():
            return True

        # Try to start the server
        try:
            subprocess.Popen(
                [sys.executable, "-m", "cli_agents.wrapper.acp_server", "--daemon"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Wait briefly for startup
            import time

            for _ in range(10):
                time.sleep(0.5)
                if self.is_available():
                    return True
            return False
        except Exception:
            logger.exception("Failed to start ACP server")
            return False

    def discover(
        self,
        query: str = "",
        tool_name: str = "",
        tool_args: str = "",
        k: int = 5,
    ) -> list[SkillMatch]:
        """Discover skills matching a query or tool context."""
        body = {"query": query, "tool_name": tool_name, "k": k}
        if tool_args:
            body["tool_args"] = tool_args

        response = self._post("/discover", body)
        return [
            SkillMatch(
                name=s["name"],
                description=s.get("description", ""),
                relevance_score=s.get("relevance_score", 0.0),
                metadata=s.get("metadata", {}),
            )
            for s in response.get("skills", [])
        ]

    def execute(
        self,
        skill_name: str,
        request: str = "",
        params: dict | None = None,
    ) -> ExecutionResult:
        """Execute a Memento skill."""
        body: dict[str, Any] = {"skill_name": skill_name, "request": request}
        if params:
            body["params"] = params

        response = self._post("/execute", body)
        return ExecutionResult(
            ok=response.get("ok", False),
            output=response.get("output", ""),
            error=response.get("error"),
            diagnostics=response.get("diagnostics", {}),
        )

    def reflect(
        self,
        tool_name: str,
        result_type: str,
        result_text: str = "",
        skill_name: str = "",
        session_id: str = "",
    ) -> ReflectionResult:
        """Record an execution outcome for reflective learning."""
        body: dict[str, Any] = {
            "tool_name": tool_name,
            "result_type": result_type,
            "result_text": result_text,
        }
        if skill_name:
            body["skill_name"] = skill_name
        if session_id:
            body["session_id"] = session_id

        response = self._post("/reflect", body)
        return ReflectionResult(
            recorded=response.get("recorded", False),
            skill_score_delta=response.get("skill_score_delta", 0.0),
            suggestion=response.get("suggestion"),
        )

    def list_skills(self) -> list[dict]:
        """List all available skills."""
        response = self._get("/skills")
        return response.get("skills", [])

    def sync(self, target: str = "copilot-cli", workspace: str = "") -> dict:
        """Sync skills to target platform format."""
        body: dict[str, Any] = {"target": target}
        if workspace:
            body["workspace"] = workspace
        return self._post("/sync", body)

    # -------------------------------------------------------------------
    # HTTP helpers
    # -------------------------------------------------------------------

    def _get(self, path: str) -> dict:
        """HTTP GET with fallback."""
        url = f"{self.base_url}{path}"
        try:
            return self._request_httpx("GET", url)
        except ImportError:
            return self._request_urllib("GET", url)

    def _post(self, path: str, body: dict) -> dict:
        """HTTP POST with fallback."""
        url = f"{self.base_url}{path}"
        try:
            return self._request_httpx("POST", url, body)
        except ImportError:
            return self._request_urllib("POST", url, body)

    def _request_httpx(
        self, method: str, url: str, body: dict | None = None
    ) -> dict:
        """Make request using httpx (preferred)."""
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(url, json=body)
            response.raise_for_status()
            return response.json()

    def _request_urllib(
        self, method: str, url: str, body: dict | None = None
    ) -> dict:
        """Make request using urllib (zero-dependency fallback)."""
        import urllib.request

        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ConnectionError(f"Failed to connect to ACP server: {exc}") from exc


# ---------------------------------------------------------------------------
# Shell-friendly functions (for use from hook scripts via python -c)
# ---------------------------------------------------------------------------


def cli_discover(query: str, tool_name: str = "") -> None:
    """CLI entry point for skill discovery. Prints JSON to stdout."""
    client = ACPClient()
    if not client.is_available():
        client.ensure_server()

    skills = client.discover(query=query, tool_name=tool_name)
    print(json.dumps([s.__dict__ for s in skills], indent=2))


def cli_reflect(
    tool_name: str, result_type: str, result_text: str = ""
) -> None:
    """CLI entry point for reflection. Prints JSON to stdout."""
    client = ACPClient()
    if not client.is_available():
        return  # Silently skip if server not available

    result = client.reflect(
        tool_name=tool_name, result_type=result_type, result_text=result_text
    )
    print(json.dumps(result.__dict__))
