"""File loading and formatting for prompt context."""

import sys
from pathlib import Path
from typing import List
import glob as glob_module


# Size limits to prevent context explosion
MAX_FILE_SIZE = 100_000  # 100KB per file
MAX_TOTAL_SIZE = 500_000  # 500KB total


def load_file(path: Path) -> str:
    """Load a single file and return its contents."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def format_file_xml(path: Path, content: str) -> str:
    """Format a file with XML-style tags."""
    return f'<file path="{path}">\n{content}\n</file>'


def expand_glob(pattern: str, base_path: Path = None) -> List[Path]:
    """Expand a glob pattern to a list of file paths."""
    if base_path:
        pattern = str(base_path / pattern)

    paths = []
    for match in glob_module.glob(pattern, recursive=True):
        p = Path(match)
        if p.is_file():
            paths.append(p)

    return sorted(paths)


def load_files(
    file_paths: List[Path] = None,
    include_patterns: List[str] = None,
    base_path: Path = None,
    max_file_size: int = MAX_FILE_SIZE,
    max_total_size: int = MAX_TOTAL_SIZE,
) -> str:
    """
    Load files and format them for inclusion in a prompt.

    Args:
        file_paths: Explicit file paths to include
        include_patterns: Glob patterns to expand
        base_path: Base directory for relative patterns
        max_file_size: Maximum size per file in bytes (default 100KB)
        max_total_size: Maximum total size in bytes (default 500KB)

    Returns:
        Formatted string with all file contents in XML tags
    """
    all_paths: List[Path] = []

    # Add explicit file paths
    if file_paths:
        for p in file_paths:
            path = Path(p)
            if path.exists() and path.is_file():
                all_paths.append(path)

    # Expand glob patterns
    if include_patterns:
        for pattern in include_patterns:
            expanded = expand_glob(pattern, base_path)
            all_paths.extend(expanded)

    # Deduplicate while preserving order
    seen = set()
    unique_paths = []
    for p in all_paths:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_paths.append(p)

    if not unique_paths:
        return ""

    # Load and format each file with size limits
    formatted_files = []
    total_size = 0

    for path in unique_paths:
        try:
            file_size = path.stat().st_size

            # Skip files over the per-file limit
            if file_size > max_file_size:
                print(f"Warning: Skipped {path}: exceeds {max_file_size // 1000}KB limit", file=sys.stderr)
                continue

            # Stop if we'd exceed total limit
            if total_size + file_size > max_total_size:
                print(f"Warning: Skipped {path}: total size limit ({max_total_size // 1000}KB) reached", file=sys.stderr)
                continue

            content = load_file(path)
            formatted = format_file_xml(path, content)
            formatted_files.append(formatted)
            total_size += file_size

        except Exception:
            # Skip files that can't be read
            pass

    return "\n\n".join(formatted_files)


def build_prompt_with_files(
    query: str,
    file_paths: List[Path] = None,
    include_patterns: List[str] = None,
) -> str:
    """
    Build the final prompt with files included.

    Args:
        query: The user's question
        file_paths: Explicit file paths
        include_patterns: Glob patterns

    Returns:
        Complete prompt with files and query
    """
    files_content = load_files(file_paths, include_patterns)

    if files_content:
        return f"{files_content}\n\n{query}"

    return query
