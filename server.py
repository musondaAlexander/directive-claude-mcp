"""
Directives MCP Server
---------------------
Serves engineering directive documents (AGENT.md and friends) to any
Claude Code instance over the MCP streamable-HTTP transport.

Documents live in the ./docs directory (mounted as a volume in Docker),
so they can be edited without rebuilding the image.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DOCS_DIR = Path(os.environ.get("DOCS_DIR", "./docs")).resolve()
PORT = int(os.environ.get("PORT", "49721"))
HOST = os.environ.get("HOST", "0.0.0.0")

mcp = FastMCP(
    "directives",
    instructions=(
        "This server provides Alexander's engineering directives and project "
        "templates. At the start of any project work, call get_directives() "
        "and follow the returned document as the source of truth for code "
        "standards, sprint structure, modularization, commit discipline, and "
        "clarification protocol. Use get_section() to re-read specific "
        "sections during work."
    ),
    host=HOST,
    port=PORT,
)


def _doc_path(name: str) -> Path:
    """Resolve a document name safely inside DOCS_DIR.

    Rejects any name that escapes DOCS_DIR (path traversal, absolute paths,
    or a sibling directory that merely shares DOCS_DIR's name prefix).
    """
    if not name.endswith(".md"):
        name = f"{name}.md"
    candidate = (DOCS_DIR / name).resolve()
    try:
        candidate.relative_to(DOCS_DIR)
    except ValueError:
        raise ValueError("Invalid document path.") from None
    return candidate


def _available_docs() -> list[str]:
    """Sorted list of served document file names."""
    return sorted(p.name for p in DOCS_DIR.glob("*.md"))


@mcp.tool()
def list_documents() -> str:
    """List all available directive/template documents on this server."""
    docs = _available_docs()
    if not docs:
        return "No documents found."
    lines = []
    for name in docs:
        first_line = ""
        try:
            with open(DOCS_DIR / name, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        first_line = line.lstrip("# ").strip()
                        break
        except OSError:
            pass
        lines.append(f"- {name}: {first_line}")
    return "\n".join(lines)


@mcp.tool()
def get_directives() -> str:
    """
    Return the master engineering directives (AGENT.md) in full.
    Call this at the start of any project session and treat the returned
    document as the authoritative source for how development is conducted.
    """
    path = _doc_path("AGENT.md")
    if not path.exists():
        return "AGENT.md not found on the directives server."
    return path.read_text(encoding="utf-8")


@mcp.tool()
def get_document(name: str) -> str:
    """
    Return a specific document by file name (e.g. 'AGENT.md',
    'CHECKLIST.md'). Use list_documents() to see what is available.
    """
    try:
        path = _doc_path(name)
    except ValueError as exc:
        return str(exc)
    if not path.exists():
        available = ", ".join(_available_docs())
        return f"Document '{name}' not found. Available: {available}"
    return path.read_text(encoding="utf-8")


@mcp.tool()
def get_section(query: str, document: str = "AGENT.md") -> str:
    """
    Return the section(s) of a document whose heading matches the query
    (case-insensitive substring match, e.g. 'sprint', 'commit', 'guard').
    Useful for re-reading one part of the directives mid-session without
    reloading the whole document.
    """
    try:
        path = _doc_path(document)
    except ValueError as exc:
        return str(exc)
    if not path.exists():
        return f"Document '{document}' not found."

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Index every level 1-3 heading with its (line number, level, text).
    headings: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,3}) ", line)
        if m:
            headings.append((i, len(m.group(1)), line.rstrip("\n")))

    q = query.lower()
    # For each matching heading, slice down to the next heading of the same or
    # higher level, so a matched parent section carries its own subsections.
    ranges: list[tuple[int, int]] = []
    for idx, (line_no, level, heading_text) in enumerate(headings):
        if q not in heading_text.lower():
            continue
        end = len(lines)
        for next_line, next_level, _ in headings[idx + 1:]:
            if next_level <= level:
                end = next_line
                break
        ranges.append((line_no, end))

    # Drop any range fully contained in another match (its parent already
    # includes it), so parent+child matches don't duplicate content.
    kept = [
        (s, e)
        for s, e in ranges
        if not any(
            os_ <= s and e <= oe and (os_, oe) != (s, e) for os_, oe in ranges
        )
    ]

    if not kept:
        return (
            f"No section heading matching '{query}' in {document}.\n"
            "Available sections:\n" + "\n".join(h[2] for h in headings)
        )
    return "\n\n".join("".join(lines[s:e]).rstrip() for s, e in kept)


@mcp.tool()
def health() -> str:
    """Health check. Returns server status and document inventory count."""
    count = len(_available_docs())
    return f"ok — directives server running, {count} document(s) in {DOCS_DIR.name}/"


def main() -> None:
    """Console-script / module entry point."""
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
