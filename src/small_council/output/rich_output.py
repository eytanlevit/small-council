"""Rich terminal output with progressive display."""

from typing import List, Dict, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class RichOutput:
    """Rich terminal output handler for council results."""

    def __init__(self, console: Console = None, quiet: bool = False):
        self.console = console or Console()
        self.quiet = quiet

    def show_stage1_start(self, model_count: int):
        """Show Stage 1 starting message."""
        if self.quiet:
            return
        self.console.print()
        self.console.print(
            f"[bold blue]Stage 1:[/] Collecting Responses from {model_count} models...",
        )

    def show_stage1_complete(self, results: List[Dict[str, Any]], total_models: int):
        """Show Stage 1 results."""
        if self.quiet:
            return

        self.console.print(
            f"[bold green]Stage 1 Complete[/] [{len(results)}/{total_models} responded]\n"
        )

        for result in results:
            model = result["model"]
            response = result["response"]

            panel = Panel(
                Markdown(response),
                title=f"[bold]{model}[/]",
                border_style="blue",
                padding=(1, 2),
            )
            self.console.print(panel)

    def show_stage2_start(self):
        """Show Stage 2 starting message."""
        if self.quiet:
            return
        self.console.print()
        self.console.print("[bold blue]Stage 2:[/] Peer Evaluation in progress...")

    def show_stage2_complete(
        self,
        results: List[Dict[str, Any]],
        aggregate_rankings: List[Dict[str, Any]]
    ):
        """Show Stage 2 results with aggregate rankings."""
        if self.quiet:
            return

        self.console.print("[bold green]Stage 2 Complete[/]\n")

        # Show aggregate rankings table
        table = Table(title="Aggregate Rankings", show_header=True)
        table.add_column("Rank", style="cyan", justify="right")
        table.add_column("Model", style="white")
        table.add_column("Avg Rank", style="green", justify="right")

        for i, ranking in enumerate(aggregate_rankings, 1):
            table.add_row(
                str(i),
                ranking["model"],
                f"{ranking['average_rank']:.2f}"
            )

        self.console.print(table)
        self.console.print()

    def show_stage3_start(self, chairman_model: str):
        """Show Stage 3 starting message."""
        if self.quiet:
            return
        self.console.print()
        self.console.print(
            f"[bold blue]Stage 3:[/] Chairman ({chairman_model}) synthesizing..."
        )

    def show_stage3_complete(self, result: Dict[str, Any]):
        """Show Stage 3 final synthesis."""
        model = result["model"]
        response = result["response"]

        self.console.print()
        self.console.rule("[bold green]FINAL ANSWER[/]", style="green")
        self.console.print(f"[dim]Chairman: {model}[/]\n")
        self.console.print(Markdown(response))
        self.console.print()

    def show_error(self, message: str):
        """Show error message."""
        self.console.print(f"[bold red]Error:[/] {message}")
