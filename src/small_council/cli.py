"""CLI entry point for Small Council."""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import click
import typer
from rich.console import Console
from typer.core import TyperGroup

from . import __version__
from .config import load_config, ConfigError
from .council import run_full_council
from .files import build_prompt_with_files
from .output import RichOutput, format_json, format_markdown


class _SubcommandAwareGroup(TyperGroup):
    """Typer group that correctly routes subcommands even when a positional
    argument is declared on the callback.

    Without this, Click's argument parser consumes the subcommand name
    (e.g. ``tmux``) as the value of the positional ``query`` argument,
    making ``small-council tmux start ...`` impossible.
    """

    def parse_args(self, ctx: click.Context, args: list) -> list:
        if (
            args
            and not args[0].startswith("-")
            and args[0] in self.list_commands(ctx)
        ):
            cmd_name = args[0]
            remaining = args[1:]
            # Parse *only* options (skip positional arguments) so that
            # the subcommand name is not consumed as a positional value.
            saved_params = self.params[:]
            self.params = [
                p for p in self.params if not isinstance(p, click.Argument)
            ]
            rest = click.Command.parse_args(self, ctx, remaining)
            self.params = saved_params
            ctx._protected_args = [cmd_name]
            ctx.args = rest
            return ctx.args
        return super().parse_args(ctx, args)


app = typer.Typer(
    name="small-council",
    help="Multi-LLM deliberation via OpenRouter",
    add_completion=False,
    cls=_SubcommandAwareGroup,
)

# Separate consoles: stderr for progress, stdout for results
stderr_console = Console(stderr=True)
stdout_console = Console()


def version_callback(value: bool):
    if value:
        stderr_console.print(f"small-council {__version__}")
        raise typer.Exit()


def get_query(query_arg: Optional[str]) -> str:
    """Get query from argument or stdin."""
    if query_arg:
        return query_arg

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    stderr_console.print("[red]Error:[/] No query provided. Pass as argument or pipe via stdin.")
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    query: Optional[str] = typer.Argument(
        None,
        help="The question to ask the council. Can also be piped via stdin.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output results as JSON",
    ),
    markdown_output: bool = typer.Option(
        False,
        "--markdown",
        "-m",
        help="Output results as Markdown",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress progress output, show only final result",
    ),
    answer_only: bool = typer.Option(
        False,
        "--answer-only",
        "-a",
        help="Output only the final synthesized answer (agent-friendly)",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (default: ~/.small-council.yaml)",
    ),
    models: Optional[str] = typer.Option(
        None,
        "--models",
        help="Comma-separated list of council models (overrides config)",
    ),
    chairman: Optional[str] = typer.Option(
        None,
        "--chairman",
        help="Chairman model (overrides config)",
    ),
    files: Optional[List[Path]] = typer.Option(
        None,
        "--file",
        "-f",
        help="Include file contents in prompt (can be repeated)",
    ),
    include: Optional[List[str]] = typer.Option(
        None,
        "--include",
        "-i",
        help="Include files matching glob pattern (can be repeated)",
    ),
    skip_ranking: Optional[List[str]] = typer.Option(
        None,
        "--skip-ranking",
        help="Model names to exclude from Stage 2 ranking (can be repeated)",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """
    Ask a question to the Small Council.

    The council consists of multiple LLMs that:
    1. Each provide an individual response
    2. Anonymously rank each other's responses
    3. Have a chairman synthesize a final answer

    Agent-friendly: When stdout is piped, automatically outputs JSON.
    Progress/errors go to stderr, keeping stdout clean for parsing.

    Examples:
        small-council "What is the meaning of life?"
        echo "Explain quantum computing" | small-council
        small-council --json "Compare Python and Rust" > result.json
        small-council -a "Quick question" | pbcopy  # just the answer
        small-council -f code.py -f readme.md "Review this code"
        small-council -i "src/**/*.py" "Analyze this codebase"
    """
    # If invoked with a subcommand, let typer handle it
    if ctx.invoked_subcommand is not None:
        return

    # Get the query
    raw_query = get_query(query)

    # Build prompt with files if specified
    user_query = build_prompt_with_files(
        raw_query,
        file_paths=files,
        include_patterns=include,
    )

    # Parse model overrides
    models_list = None
    if models:
        models_list = [m.strip() for m in models.split(",")]

    # Load config
    try:
        config = load_config(
            config_path=config_path,
            models_override=models_list,
            chairman_override=chairman,
            skip_ranking_override=skip_ranking,
        )
    except ConfigError as e:
        stderr_console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)

    # Determine output mode
    # Auto-detect: if stdout is piped and no format specified, use JSON
    stdout_is_tty = sys.stdout.isatty()
    use_json = json_output or (not stdout_is_tty and not markdown_output and not answer_only)
    use_markdown = markdown_output
    use_answer_only = answer_only
    use_rich = not (use_json or use_markdown or use_answer_only) and stdout_is_tty

    # Create output handler for rich mode (uses stderr for progress)
    output = RichOutput(stderr_console, quiet=quiet or not use_rich)

    # Store total model count for callback
    total_models = len(config.council_models)

    # Run the council
    async def run():
        if use_rich:
            output.show_stage1_start(total_models)

        async def on_stage_complete(stage: str, data):
            if use_rich:
                if stage == "stage1":
                    output.show_stage1_complete(data, total_models)
                    output.show_stage2_start()
                elif stage == "stage2":
                    output.show_stage2_complete(
                        data["results"],
                        data["aggregate_rankings"]
                    )
                    output.show_stage3_start(config.chairman_model)
                elif stage == "stage3":
                    output.show_stage3_complete(data)

        stage1, stage2, stage3, metadata = await run_full_council(
            user_query=user_query,
            council_models=config.council_models,
            chairman_model=config.chairman_model,
            api_key=config.api_key,
            api_url=config.api_url,
            timeout=config.timeout,
            max_tokens=config.max_tokens,
            model_timeouts=config.model_timeouts,
            on_stage_complete=on_stage_complete if use_rich else None,
            skip_ranking_models=config.skip_ranking_models or None,
        )

        return stage1, stage2, stage3, metadata

    try:
        stage1, stage2, stage3, metadata = asyncio.run(run())
    except KeyboardInterrupt:
        stderr_console.print("\n[yellow]Interrupted[/]")
        raise typer.Exit(130)

    # Format output for non-rich modes
    if use_answer_only:
        # Just the final answer, clean for agents
        print(stage3.get("response", ""))
    elif use_json:
        print(format_json(user_query, stage1, stage2, stage3, metadata))
    elif use_markdown:
        print(format_markdown(user_query, stage1, stage2, stage3, metadata))


# ---------------------------------------------------------------------------
# Tmux subcommand group
# ---------------------------------------------------------------------------

tmux_app = typer.Typer(
    name="tmux",
    help="Tmux session management for long-running council queries",
)
app.add_typer(tmux_app)


@tmux_app.command("start")
def tmux_start(
    prompt: Optional[str] = typer.Option(
        None,
        "--prompt",
        "-p",
        help="The prompt to send to the council",
    ),
    prompt_file: Optional[Path] = typer.Option(
        None,
        "--prompt-file",
        "-P",
        help="Path to a file containing the prompt",
    ),
    files: Optional[List[str]] = typer.Option(
        None,
        "--file",
        "-f",
        help="Include file contents in prompt (can be repeated)",
    ),
):
    """Start a Small Council session in a detached tmux window."""
    from .tmux import start

    # Resolve prompt
    resolved_prompt = prompt
    if prompt_file is not None:
        if not prompt_file.exists():
            stderr_console.print(f"[red]Error:[/] Prompt file not found: {prompt_file}")
            raise typer.Exit(1)
        resolved_prompt = prompt_file.read_text()

    if not resolved_prompt:
        stderr_console.print("[red]Error:[/] No prompt provided. Use -p 'prompt' or -P /path/to/file")
        raise typer.Exit(1)

    start(prompt=resolved_prompt, files=files or None)


@tmux_app.command("wait")
def tmux_wait(
    session_id: str = typer.Argument(..., help="The tmux session ID to wait for"),
    timeout: int = typer.Option(
        1800,
        "--timeout",
        "-t",
        help="Maximum seconds to wait (default 1800)",
    ),
    poll_interval: int = typer.Option(
        10,
        "--poll-interval",
        "-i",
        help="Seconds between status checks (default 10)",
    ),
):
    """Wait for a Small Council tmux session to complete."""
    from .tmux import wait

    wait(session_id=session_id, timeout=timeout, poll_interval=poll_interval)


@tmux_app.command("status")
def tmux_status(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to check"),
    list_all: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all council sessions",
    ),
):
    """Check status of Small Council tmux sessions."""
    from .tmux import status

    status(session_id=session_id, list_all=list_all)


@tmux_app.command("cleanup")
def tmux_cleanup(
    older_than: float = typer.Option(
        1.0,
        "--older-than",
        help="Clean sessions older than this many hours (default 1)",
    ),
    all_sessions: bool = typer.Option(
        False,
        "--all",
        help="Clean ALL council sessions",
    ),
):
    """Clean up old Small Council tmux sessions and temp files."""
    from .tmux import cleanup

    cleanup(older_than=older_than, all_sessions=all_sessions)


if __name__ == "__main__":
    app()
