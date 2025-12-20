"""Markdown output formatter."""

from typing import List, Dict, Any


def format_markdown(
    query: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    metadata: Dict[str, Any]
) -> str:
    """
    Format council results as Markdown.

    Args:
        query: Original user query
        stage1: Stage 1 results
        stage2: Stage 2 results
        stage3: Stage 3 result
        metadata: Metadata including label_to_model and aggregate_rankings

    Returns:
        Markdown string
    """
    lines = []

    lines.append("# Council Deliberation\n")
    lines.append(f"**Query:** {query}\n")

    # Stage 1
    lines.append("## Stage 1: Individual Responses\n")
    for result in stage1:
        lines.append(f"### {result['model']}\n")
        lines.append(result['response'])
        lines.append("\n")

    # Stage 2 - Aggregate Rankings
    lines.append("## Stage 2: Peer Evaluation\n")
    lines.append("### Aggregate Rankings\n")
    lines.append("| Rank | Model | Average Score |")
    lines.append("|------|-------|---------------|")

    aggregate = metadata.get("aggregate_rankings", [])
    for i, ranking in enumerate(aggregate, 1):
        model = ranking["model"]
        avg = ranking["average_rank"]
        lines.append(f"| {i} | {model} | {avg} |")

    lines.append("\n")

    # Stage 3
    lines.append("## Stage 3: Final Synthesis\n")
    lines.append(f"**Chairman:** {stage3['model']}\n")
    lines.append(stage3['response'])
    lines.append("\n")

    return "\n".join(lines)
