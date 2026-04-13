"""ACP Wrapper Server — Expose Memento-Skills via REST API.

This module implements an ACP-compatible HTTP server that wraps the
Memento-Skills core functionality (SkillGateway, SkillExecutor, Reflection)
and exposes it as REST endpoints callable from CLI agent hook scripts.

Endpoints:
    GET  /health    → Server health check
    POST /discover  → Search skills by query
    POST /execute   → Execute a skill
    POST /reflect   → Record execution outcome
    GET  /skills    → List all available skills
    POST /sync      → Sync skills to target platform format
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

from aiohttp import web

logger = logging.getLogger("memento.acp_server")

# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — Server health and status."""
    app_state = request.app.get("memento_state", {})
    return web.json_response(
        {
            "status": "ok",
            "version": "0.1.0",
            "skills_loaded": app_state.get("skills_count", 0),
            "sessions_active": app_state.get("sessions_active", 0),
        }
    )


async def handle_discover(request: web.Request) -> web.Response:
    """POST /discover — Search skills matching a query.

    Request body:
        {
            "query": "string - search query or tool context",
            "tool_name": "string (optional) - current tool being used",
            "tool_args": "string (optional) - tool arguments",
            "k": 5  // max results
        }

    Response:
        {
            "skills": [
                {
                    "name": "skill-name",
                    "description": "...",
                    "relevance_score": 0.85,
                    "metadata": {...}
                }
            ]
        }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    query = body.get("query", "")
    tool_name = body.get("tool_name", "")
    k = body.get("k", 5)

    if not query and not tool_name:
        return web.json_response(
            {"error": "Either 'query' or 'tool_name' is required"}, status=400
        )

    # Build search query from context
    search_query = query or f"tool:{tool_name}"
    if tool_name and query:
        search_query = f"{query} (using tool: {tool_name})"

    gateway = request.app.get("skill_gateway")
    if gateway is None:
        # Fallback: scan skill files directly
        skills = await _discover_from_files(
            request.app["skills_dir"], search_query, k
        )
        return web.json_response({"skills": skills})

    try:
        manifests = await gateway.discover(
            strategy="multi_recall", query=search_query, k=k
        )
        skills = [
            {
                "name": m.name,
                "description": m.description,
                "relevance_score": getattr(m, "score", 0.0),
                "metadata": getattr(m, "metadata", {}),
            }
            for m in manifests
        ]
        return web.json_response({"skills": skills})
    except Exception as exc:
        logger.exception("Skill discovery failed")
        return web.json_response(
            {"error": str(exc), "skills": []}, status=500
        )


async def handle_execute(request: web.Request) -> web.Response:
    """POST /execute — Execute a Memento skill.

    Request body:
        {
            "skill_name": "string - skill identifier",
            "request": "string - what to do",
            "params": {...}  // optional parameters
        }

    Response:
        {
            "ok": true/false,
            "output": "string - execution result",
            "error": "string (optional) - error message",
            "diagnostics": {...}
        }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    skill_name = body.get("skill_name")
    skill_request = body.get("request", "")
    params = body.get("params", {})

    if not skill_name:
        return web.json_response(
            {"error": "'skill_name' is required"}, status=400
        )

    gateway = request.app.get("skill_gateway")
    if gateway is None:
        return web.json_response(
            {"error": "SkillGateway not initialized. Start with full bootstrap."},
            status=503,
        )

    try:
        result = await gateway.execute(
            skill_name=skill_name, request=skill_request, params=params
        )
        return web.json_response(
            {
                "ok": result.ok,
                "output": result.output,
                "error": getattr(result, "error", None),
                "diagnostics": getattr(result, "diagnostics", {}),
            }
        )
    except Exception as exc:
        logger.exception("Skill execution failed")
        return web.json_response(
            {"ok": False, "output": "", "error": str(exc)}, status=500
        )


async def handle_reflect(request: web.Request) -> web.Response:
    """POST /reflect — Record execution outcome for reflective learning.

    Request body:
        {
            "skill_name": "string - skill that was used (or empty)",
            "tool_name": "string - tool that was executed",
            "tool_args": "string - tool arguments",
            "result_type": "success" | "failure" | "denied",
            "result_text": "string - result summary",
            "session_id": "string (optional)"
        }

    Response:
        {
            "recorded": true,
            "skill_score_delta": 0.1,
            "suggestion": "string (optional) - improvement suggestion"
        }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    skill_name = body.get("skill_name", "")
    tool_name = body.get("tool_name", "")
    result_type = body.get("result_type", "success")
    result_text = body.get("result_text", "")

    # Record the outcome
    outcome = {
        "skill_name": skill_name,
        "tool_name": tool_name,
        "result_type": result_type,
        "result_text": result_text[:500],  # Truncate for storage
    }

    # Store in session history
    history: list = request.app.setdefault("reflection_history", [])
    history.append(outcome)

    # Update skill score if gateway is available
    score_delta = 0.0
    suggestion = None
    gateway = request.app.get("skill_gateway")
    if gateway and skill_name:
        try:
            if result_type == "success":
                score_delta = 0.1
            elif result_type == "failure":
                score_delta = -0.05
                suggestion = (
                    f"Skill '{skill_name}' failed on tool '{tool_name}'. "
                    "Consider reviewing the skill specification for edge cases."
                )
        except Exception:
            logger.exception("Reflection recording failed")

    response: dict[str, Any] = {"recorded": True, "skill_score_delta": score_delta}
    if suggestion:
        response["suggestion"] = suggestion

    return web.json_response(response)


async def handle_list_skills(request: web.Request) -> web.Response:
    """GET /skills — List all available skills."""
    gateway = request.app.get("skill_gateway")
    if gateway:
        try:
            skills = await gateway.list_all()
            skill_list = [
                {
                    "name": s.name,
                    "description": getattr(s, "description", ""),
                }
                for s in skills.values()
            ]
            return web.json_response({"skills": skill_list})
        except Exception as exc:
            logger.exception("Failed to list skills")
            return web.json_response({"error": str(exc)}, status=500)

    # Fallback: scan files
    skills = await _list_skills_from_files(request.app["skills_dir"])
    return web.json_response({"skills": skills})


async def handle_sync(request: web.Request) -> web.Response:
    """POST /sync — Sync Memento skills to target platform format.

    Request body:
        {
            "target": "copilot-cli" | "kiro",
            "workspace": "/path/to/workspace"  // optional
        }

    Response:
        {
            "synced": 5,
            "target": "copilot-cli",
            "output_dir": "/path/to/.github/skills"
        }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    target = body.get("target", "copilot-cli")
    workspace = Path(body.get("workspace", Path.cwd()))

    # Import converter
    from cli_agents.skills.converter import SkillConverter

    converter = SkillConverter(
        source_dir=request.app["skills_dir"], target=target, workspace=workspace
    )

    try:
        count, output_dir = await converter.sync_all()
        return web.json_response(
            {"synced": count, "target": target, "output_dir": str(output_dir)}
        )
    except Exception as exc:
        logger.exception("Skill sync failed")
        return web.json_response({"error": str(exc)}, status=500)


# ---------------------------------------------------------------------------
# File-based fallback helpers (when SkillGateway is not available)
# ---------------------------------------------------------------------------


async def _discover_from_files(
    skills_dir: Path, query: str, k: int
) -> list[dict]:
    """Simple file-based skill discovery (fallback)."""
    skills = []
    query_lower = query.lower()

    if not skills_dir.exists():
        return skills

    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        content = skill_md.read_text(errors="replace")
        # Simple keyword matching
        name = skill_path.name
        description = _extract_description(content)
        score = _simple_relevance(query_lower, name, description, content)

        if score > 0.0:
            skills.append(
                {
                    "name": name,
                    "description": description,
                    "relevance_score": round(score, 3),
                    "metadata": {},
                }
            )

    skills.sort(key=lambda s: s["relevance_score"], reverse=True)
    return skills[:k]


async def _list_skills_from_files(skills_dir: Path) -> list[dict]:
    """List skills by scanning the filesystem."""
    skills = []
    if not skills_dir.exists():
        return skills

    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        content = skill_md.read_text(errors="replace")
        skills.append(
            {
                "name": skill_path.name,
                "description": _extract_description(content),
            }
        )
    return skills


def _extract_description(content: str) -> str:
    """Extract the description from SKILL.md frontmatter."""
    import re

    match = re.search(
        r"^---\s*\n(.*?)\n---", content, re.DOTALL | re.MULTILINE
    )
    if match:
        frontmatter = match.group(1)
        desc_match = re.search(
            r"description:\s*[\"']?(.*?)[\"']?\s*$", frontmatter, re.MULTILINE
        )
        if desc_match:
            return desc_match.group(1).strip()
    return ""


def _simple_relevance(
    query: str, name: str, description: str, content: str
) -> float:
    """Compute simple keyword relevance score."""
    query_terms = query.split()
    if not query_terms:
        return 0.0

    score = 0.0
    for term in query_terms:
        term = term.lower()
        if term in name.lower():
            score += 0.4
        if term in description.lower():
            score += 0.3
        if term in content.lower():
            score += 0.1

    return min(score / max(len(query_terms), 1), 1.0)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(
    skills_dir: Path | None = None,
    skill_gateway: Any | None = None,
) -> web.Application:
    """Create the ACP wrapper web application."""
    app = web.Application()

    # Store references
    app["skills_dir"] = skills_dir or Path.home() / "memento_s" / "workspace" / "skills"
    if skill_gateway:
        app["skill_gateway"] = skill_gateway
    app["memento_state"] = {"skills_count": 0, "sessions_active": 0}

    # Register routes
    app.router.add_get("/health", handle_health)
    app.router.add_post("/discover", handle_discover)
    app.router.add_post("/execute", handle_execute)
    app.router.add_post("/reflect", handle_reflect)
    app.router.add_get("/skills", handle_list_skills)
    app.router.add_post("/sync", handle_sync)

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 47200,
    skills_dir: Path | None = None,
    daemon: bool = False,
) -> None:
    """Start the ACP wrapper server.

    Args:
        host: Bind address (default: localhost only for security).
        port: Port number (default: 47200).
        skills_dir: Path to Memento skills directory.
        daemon: If True, fork into background.
    """
    if daemon:
        _daemonize(host, port, skills_dir)
        return

    app = create_app(skills_dir=skills_dir)
    logger.info("Starting ACP server on %s:%d", host, port)
    web.run_app(app, host=host, port=port, print=None)


def _daemonize(
    host: str, port: int, skills_dir: Path | None
) -> None:
    """Fork into a background daemon process."""
    import platform

    if platform.system() == "Windows":
        logger.error(
            "Daemon mode is not supported on Windows. "
            "Run the server in the foreground or use a service manager."
        )
        return

    pid_file = Path.home() / "memento_s" / "memento-acp.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if already running
    if pid_file.exists():
        try:
            existing_pid = int(pid_file.read_text().strip())
            os.kill(existing_pid, 0)  # Check if process exists
            logger.info("ACP server already running (PID %d)", existing_pid)
            return
        except (OSError, ValueError):
            pid_file.unlink(missing_ok=True)

    pid = os.fork()
    if pid > 0:
        # Parent process
        pid_file.write_text(str(pid))
        logger.info("ACP server started as daemon (PID %d)", pid)
        return

    # Child process — become session leader
    os.setsid()

    # Redirect stdio
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)

    # Write actual PID
    pid_file.write_text(str(os.getpid()))

    # Handle SIGTERM for clean shutdown
    def _on_sigterm(signum: int, frame: Any) -> None:
        pid_file.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _on_sigterm)

    # Run the server
    app = create_app(skills_dir=skills_dir)
    web.run_app(app, host=host, port=port, print=None)


def stop_server() -> bool:
    """Stop the daemon server if running."""
    pid_file = Path.home() / "memento_s" / "memento-acp.pid"
    if not pid_file.exists():
        return False

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        return True
    except (OSError, ValueError):
        pid_file.unlink(missing_ok=True)
        return False


def is_server_running() -> bool:
    """Check if the ACP server daemon is running."""
    pid_file = Path.home() / "memento_s" / "memento-acp.pid"
    if not pid_file.exists():
        return False

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Memento ACP Wrapper Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=47200)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.stop:
        if stop_server():
            print("Server stopped.")
        else:
            print("Server not running.")
    elif args.status:
        if is_server_running():
            print("Server is running.")
        else:
            print("Server is not running.")
    else:
        logging.basicConfig(level=logging.INFO)
        run_server(host=args.host, port=args.port, daemon=args.daemon)
