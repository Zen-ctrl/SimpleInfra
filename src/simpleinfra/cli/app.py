"""Main CLI application for SimpleInfra."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

try:
    import typer
    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

from ..dsl.parser import SimpleInfraParser
from ..engine.executor import TaskExecutor
from ..engine.planner import ExecutionPlanner
from ..modules.registry import create_default_registry
from .output import OutputPrinter

if TYPER_AVAILABLE:
    app = typer.Typer(
        name="si",
        help="SimpleInfra -- Infrastructure as Code, simplified.",
        no_args_is_help=True,
    )
else:
    app = None


def _run_command(
    file: Path,
    task: str | None = None,
    plan: bool = False,
    verbose: bool = False,
) -> int:
    """Execute a .si file."""
    output = OutputPrinter(verbose=verbose)
    output.banner()

    if not file.exists():
        output.error(f"File not found: {file}")
        return 1

    try:
        # Parse the file
        parser = SimpleInfraParser()
        document = parser.parse_file(file)

        # Show plan if requested
        if plan:
            planner = ExecutionPlanner(document)

            # Determine which tasks to plan
            if task:
                task_names = [task]
            elif document.tasks:
                task_names = [t.name for t in document.tasks]
            else:
                output.error("No tasks found in file")
                return 1

            # Show plan for each task
            for task_name in task_names:
                plan_data = planner.plan_task(task_name)

                if "error" in plan_data:
                    output.error(plan_data["error"])
                    return 1

                output.plan(plan_data)

            return 0

        # Execute task
        registry = create_default_registry()
        executor = TaskExecutor(
            document=document,
            registry=registry,
            project_dir=file.parent,
            dry_run=False,
        )

        # Determine which tasks to run
        if task:
            # Run specific task only
            task_names = [task]
        elif document.tasks:
            # Run ALL tasks in sequence
            task_names = [t.name for t in document.tasks]
        else:
            output.error("No tasks found in file")
            return 1

        # Run tasks in sequence
        all_success = True
        for task_name in task_names:
            output.print(f"\nRunning task: [bold]{task_name}[/bold]\n", style="cyan")
            results = asyncio.run(executor.run_task(task_name))

            # Show results
            for target_result in results.get("results", []):
                output.task_start(task_name, target_result["target"])
                for action in target_result.get("actions", []):
                    output.action_result(action)

            output.task_summary(results)

            # Stop on first failure
            if not results.get("success"):
                all_success = False
                output.error(f"Task '{task_name}' failed. Stopping execution.")
                break

        return 0 if all_success else 1

    except Exception as e:
        output.error(str(e))
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def _validate_command(file: Path) -> int:
    """Validate a .si file without executing it."""
    output = OutputPrinter()

    if not file.exists():
        output.error(f"File not found: {file}")
        return 1

    try:
        parser = SimpleInfraParser()
        document = parser.parse_file(file)
        output.success(f"File is valid: {file}")
        output.print(f"  - {len(document.tasks)} tasks")
        output.print(f"  - {len(document.servers)} servers")
        output.print(f"  - {len(document.variables)} variables")
        return 0
    except Exception as e:
        output.error(f"Validation failed: {e}")
        return 1


def _init_command() -> int:
    """Initialize a new SimpleInfra project."""
    output = OutputPrinter()

    # Create example.si
    example_content = '''# SimpleInfra Example File

# Variables
set app_name "myapp"

# Define a server (or use 'local' for the local machine)
server web:
    host "192.168.1.10"
    user "root"
    key "~/.ssh/id_rsa"

# Task
task "Hello World" on local:
    run "echo Hello from SimpleInfra!"
'''

    example_file = Path("example.si")
    if example_file.exists():
        output.error("example.si already exists")
        return 1

    example_file.write_text(example_content, encoding="utf-8")
    output.success("Created example.si")
    output.print("\nTry running:")
    output.print("  si run example.si")
    output.print("  si validate example.si")
    output.print("  si run example.si --plan")
    return 0


def main() -> None:
    """Main CLI entry point."""
    if not TYPER_AVAILABLE or app is None:
        print("Error: typer is not installed. Install with: pip install typer")
        sys.exit(1)

    @app.command()
    def run(
        file: Path = typer.Argument(..., help="Path to a .si file"),
        task: str = typer.Option(None, "--task", "-t", help="Run a specific task"),
        plan: bool = typer.Option(False, "--plan", "-p", help="Show execution plan without running"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    ) -> None:
        """Execute tasks from a .si file."""
        exit_code = _run_command(file, task, plan, verbose)
        raise typer.Exit(code=exit_code)

    @app.command()
    def validate(
        file: Path = typer.Argument(..., help="Path to a .si file"),
    ) -> None:
        """Validate a .si file for syntax and semantic errors."""
        exit_code = _validate_command(file)
        raise typer.Exit(code=exit_code)

    @app.command()
    def init() -> None:
        """Create a new SimpleInfra project with an example file."""
        exit_code = _init_command()
        raise typer.Exit(code=exit_code)

    @app.command()
    def version() -> None:
        """Show SimpleInfra version."""
        from .. import __version__
        print(f"SimpleInfra version {__version__}")

    app()


if __name__ == "__main__":
    main()
