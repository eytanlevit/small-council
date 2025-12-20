"""CLI entry point for Small Council."""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from . import __version__
from .config import load_config, ConfigError
from .council import run_full_council
from .files import build_prompt_with_files
from .output import RichOutput, format_json, format_markdown

app = typer.Typer(
    name="small-council",
    help="Multi-LLM deliberation via OpenRouter",
    add_completion=False,
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


@app.command()
def main(
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

    # Run the council
    async def run():
        if use_rich:
            output.show_stage1_start(len(config.council_models))

        async def on_stage_complete(stage: str, data):
            if use_rich:
                if stage == "stage1":
                    output.show_stage1_complete(data)
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
            on_stage_complete=on_stage_complete if use_rich else None,
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


if __name__ == "__main__":
    app()
