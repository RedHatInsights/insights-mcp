#!/usr/bin/env python3
"""Generate a markdown table of MCP tool input token counts."""

import argparse
import sys
from pathlib import Path

import tiktoken

from insights_mcp.tool_tokens import (
    DEFAULT_TIKTOKEN_ENCODING,
    build_catalog_rows,
    default_catalog_modes,
    format_markdown_table,
)


def main() -> int:
    """Build the tool token overview and write it to a markdown file."""
    parser = argparse.ArgumentParser(description="Dump MCP tool input token counts as markdown.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output markdown file path (e.g. docs/tool-tokens.md)",
    )
    parser.add_argument(
        "--encoding",
        default=DEFAULT_TIKTOKEN_ENCODING,
        help=f"tiktoken encoding name (default: {DEFAULT_TIKTOKEN_ENCODING})",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=("stdio", "http", "sse"),
        help="MCP transport used to fetch tools (default: stdio)",
    )
    args = parser.parse_args()

    encoding = tiktoken.get_encoding(args.encoding)
    rows = build_catalog_rows(default_catalog_modes(), encoding, transport=args.transport)
    markdown = format_markdown_table(rows, encoding_name=args.encoding)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.output} ({len(rows)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
