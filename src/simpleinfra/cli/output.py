"""Rich-based pretty console output for SimpleInfra CLI."""

from __future__ import annotations

from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class OutputPrinter:
    """Pretty printer for CLI output using Rich."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

    def print(self, text: str, style: str = "") -> None:
        """Print text with optional styling."""
        if self.console:
            self.console.print(text, style=style)
        else:
            print(text)

    def banner(self) -> None:
        """Print SimpleInfra banner."""
        if self.console:
            self.console.print(Panel(
                "[bold cyan]SimpleInfra[/bold cyan] -- Infrastructure as Code, simplified.",
                box=box.ROUNDED,
            ))
        else:
            print("=" * 60)
            print("SimpleInfra -- Infrastructure as Code, simplified.")
            print("=" * 60)

    def task_start(self, task_name: str, target: str) -> None:
        """Print task start."""
        if self.console:
            self.console.print(f"\n[bold green]TASK[/bold green] [{task_name}] on [cyan]{target}[/cyan]")
            self.console.print("[dim]" + "-" * 50 + "[/dim]")
        else:
            print(f"\nTASK [{task_name}] on {target}")
            print("-" * 50)

    def action_result(self, action: dict[str, Any]) -> None:
        """Print action result."""
        success = action.get("success", False)
        changed = action.get("changed", False)
        message = action.get("message", "")

        if self.console:
            status = "[green]ok[/green]" if success else "[red]FAILED[/red]"
            change_marker = " [yellow](changed)[/yellow]" if changed else ""
            self.console.print(f"  {status}{change_marker}  {message}")

            if self.verbose and action.get("details"):
                details = action["details"]
                if details.get("stdout"):
                    self.console.print(f"    [dim]stdout:[/dim] {details['stdout'][:200]}")
                if details.get("stderr"):
                    self.console.print(f"    [dim]stderr:[/dim] {details['stderr'][:200]}")
        else:
            status = "ok" if success else "FAILED"
            change_marker = " (changed)" if changed else ""
            print(f"  {status}{change_marker}  {message}")

            if self.verbose and action.get("details"):
                details = action["details"]
                if details.get("stdout"):
                    print(f"    stdout: {details['stdout'][:200]}")
                if details.get("stderr"):
                    print(f"    stderr: {details['stderr'][:200]}")

    def task_summary(self, results: dict[str, Any]) -> None:
        """Print task execution summary."""
        if self.console:
            success = "[green]SUCCESS[/green]" if results.get("success") else "[red]FAILED[/red]"
            self.console.print(f"\n{success} - Task '{results.get('task_name')}' completed")
        else:
            success = "SUCCESS" if results.get("success") else "FAILED"
            print(f"\n{success} - Task '{results.get('task_name')}' completed")

    def plan(self, plan_data: dict[str, Any]) -> None:
        """Print execution plan."""
        if self.console:
            self.console.print(f"\n[bold blue]Execution Plan:[/bold blue] {plan_data.get('task')}")
            self.console.print(f"[cyan]Target:[/cyan] {plan_data.get('target')}")
            self.console.print("\n[bold]Actions:[/bold]")
            for i, action in enumerate(plan_data.get("actions", []), 1):
                self.console.print(f"  {i}. [{action['type']}] {action['description']}")
        else:
            print(f"\nExecution Plan: {plan_data.get('task')}")
            print(f"Target: {plan_data.get('target')}")
            print("\nActions:")
            for i, action in enumerate(plan_data.get("actions", []), 1):
                print(f"  {i}. [{action['type']}] {action['description']}")

    def error(self, message: str) -> None:
        """Print error message."""
        if self.console:
            self.console.print(f"[bold red]Error:[/bold red] {message}")
        else:
            print(f"Error: {message}")

    def success(self, message: str) -> None:
        """Print success message."""
        # Use [OK] instead of checkmark to avoid Windows encoding issues
        if self.console:
            self.console.print(f"[green][OK][/green] {message}")
        else:
            print(f"[OK] {message}")
