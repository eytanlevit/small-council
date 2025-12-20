"""JSON output formatter."""

import json
from typing import List, Dict, Any


def format_json(
    query: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    metadata: Dict[str, Any]
) -> str:
    """
    Format council results as JSON.

    Args:
        query: Original user query
        stage1: Stage 1 results
        stage2: Stage 2 results
        stage3: Stage 3 result
        metadata: Metadata including label_to_model and aggregate_rankings

    Returns:
        JSON string
    """
    return json.dumps({
        "query": query,
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
        "metadata": metadata
    }, indent=2)
