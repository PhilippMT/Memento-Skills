"""CLI commands for adapting Memento-Skills to CLI coding agents.

Provides the `memento adapt` and `memento serve` commands for setting up
and running the integration with GitHub Copilot CLI and Kiro.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def adapt_command(
    target: str | None = None,
    workspace: str | None = None,
    auto: bool = False,
    verify: bool = False,
) -> None:
    """Set up Memento-Skills integration with a CLI coding agent.

    Auto-detects the CLI agent environment or accepts an explicit target.
    Installs hooks, converts skills, and optionally starts the ACP server.
    """
    if verify:
        _verify_command(target, workspace)
        return

    from cli_agents.auto.bootstrap import run_bootstrap

    console.print("\n[bold blue]🔧 Memento-Skills CLI Agent Adapter[/bold blue]\n")

    if auto and not target:
        from cli_agents.auto.detector import detect_cli_agent

        detection = detect_cli_agent(Path(workspace) if workspace else Path.cwd())
        if detection.is_detected:
            target = detection.agent
            console.print(
                f"  [green]✓[/green] Auto-detected: [bold]{target}[/bold] "
                f"(confidence: {detection.confidence:.0%})"
            )
        else:
            console.print(
                "  [yellow]⚠[/yellow] No CLI agent detected. "
                "Use --target to specify one."
            )
            console.print("    Supported: copilot-cli, kiro")
            raise typer.Exit(1)

    if not target:
        console.print(
            "  [yellow]⚠[/yellow] Please specify a target platform.\n"
            "    --target copilot-cli   GitHub Copilot CLI\n"
            "    --target kiro          Kiro IDE/CLI\n"
            "    --auto                 Auto-detect\n"
        )
        raise typer.Exit(1)

    console.print(f"  Target: [bold]{target}[/bold]")
    console.print(f"  Workspace: {workspace or Path.cwd()}\n")

    with console.status("[bold green]Setting up integration..."):
        results = run_bootstrap(target=target, workspace=workspace)

    # Display results
    table = Table(title="Setup Results", show_header=True)
    table.add_column("Step", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    for step_name, step_data in results.get("steps", {}).items():
        status = step_data.get("status", "unknown")
        status_icon = {
            "ok": "[green]✓ OK[/green]",
            "error": "[red]✗ Error[/red]",
            "skipped": "[yellow]⊘ Skipped[/yellow]",
        }.get(status, status)

        details = ""
        if status == "error":
            details = step_data.get("error", "")
        elif step_name == "hooks":
            scripts = step_data.get("scripts", step_data.get("hooks", []))
            details = f"{len(scripts)} hook(s) installed"
        elif step_name == "skills":
            details = f"{step_data.get('skills_synced', 0)} skills synced"
        elif step_name == "verify":
            running = step_data.get("server_running", False)
            details = f"Server {'running' if running else 'not running'}"

        table.add_row(step_name.title(), status_icon, details)

    console.print(table)

    if results.get("success"):
        console.print(
            "\n[bold green]✓ Setup complete![/bold green] "
            "Start your CLI agent session to activate Memento integration.\n"
        )
        if not results.get("steps", {}).get("verify", {}).get("server_running"):
            console.print(
                "  [dim]Tip: Start the ACP server with:[/dim] "
                "[bold]memento serve --daemon[/bold]\n"
            )
    else:
        console.print(
            "\n[bold red]✗ Setup encountered errors.[/bold red] "
            "Check the table above for details.\n"
        )


def _verify_command(target: str | None, workspace: str | None) -> None:
    """Verify the integration is correctly set up."""
    from cli_agents.adapters.copilot_cli import get_adapter  # get_adapter is a factory that returns CopilotCLIAdapter or KiroAdapter
    from cli_agents.wrapper.acp_client import ACPClient

    ws = Path(workspace) if workspace else Path.cwd()

    console.print("\n[bold blue]🔍 Verifying Memento Integration[/bold blue]\n")

    # Determine target
    if not target:
        from cli_agents.auto.detector import detect_cli_agent

        detection = detect_cli_agent(ws)
        target = detection.agent if detection.is_detected else "copilot-cli"

    adapter = get_adapter(target, ws)
    results = adapter.verify()

    table = Table(title=f"Verification: {target}", show_header=True)
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="bold")

    for key, value in results.items():
        icon = "[green]✓[/green]" if value else "[red]✗[/red]"
        table.add_row(key.replace("_", " ").title(), f"{icon} {value}")

    # Check ACP server
    client = ACPClient()
    server_ok = client.is_available()
    table.add_row(
        "ACP Server",
        f"{'[green]✓[/green] Running' if server_ok else '[yellow]⊘ Not running[/yellow]'}",
    )

    if server_ok:
        health = client.health()
        table.add_row(
            "Skills Loaded",
            str(health.get("skills_loaded", 0)),
        )

    console.print(table)
    console.print()


def serve_command(
    host: str = "127.0.0.1",
    port: int = 47200,
    daemon: bool = False,
    stop: bool = False,
    status: bool = False,
) -> None:
    """Manage the Memento ACP wrapper server.

    The ACP server exposes Memento-Skills capabilities via REST API,
    allowing CLI agent hook scripts to discover, execute, and learn
    from skills.
    """
    from cli_agents.wrapper.acp_server import (
        run_server,
        stop_server,
        is_server_running,
    )

    if status:
        running = is_server_running()
        if running:
            console.print("[green]✓ ACP server is running[/green]")

            from cli_agents.wrapper.acp_client import ACPClient

            client = ACPClient(base_url=f"http://{host}:{port}")
            try:
                health = client.health()
                console.print(f"  URL: http://{host}:{port}")
                console.print(f"  Skills loaded: {health.get('skills_loaded', 0)}")
            except Exception:
                console.print(f"  URL: http://{host}:{port}")
        else:
            console.print("[yellow]⊘ ACP server is not running[/yellow]")
            console.print("  Start with: memento serve --daemon")
        return

    if stop:
        if stop_server():
            console.print("[green]✓ ACP server stopped[/green]")
        else:
            console.print("[yellow]⊘ ACP server was not running[/yellow]")
        return

    # Start server
    if daemon:
        console.print(
            f"[bold blue]Starting ACP server as daemon on "
            f"http://{host}:{port}...[/bold blue]"
        )
    else:
        console.print(
            f"[bold blue]Starting ACP server on "
            f"http://{host}:{port}...[/bold blue]"
        )
        console.print("  Press Ctrl+C to stop.\n")

    # Find skills directory
    skills_dir = Path.home() / "memento_s" / "workspace" / "skills"
    builtin_skills = Path(__file__).resolve().parent.parent.parent / "builtin" / "skills"
    if not skills_dir.exists() and builtin_skills.exists():
        skills_dir = builtin_skills

    run_server(host=host, port=port, skills_dir=skills_dir, daemon=daemon)

    if daemon:
        # Check if it started
        import time

        time.sleep(1)
        if is_server_running():
            console.print(f"[green]✓ ACP server started on http://{host}:{port}[/green]")
        else:
            console.print("[red]✗ ACP server failed to start[/red]")
