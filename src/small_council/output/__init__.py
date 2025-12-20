"""Output formatters for Small Council."""

from .rich_output import RichOutput
from .json_output import format_json
from .markdown_output import format_markdown

__all__ = ["RichOutput", "format_json", "format_markdown"]
