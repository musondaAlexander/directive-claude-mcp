"""
Smoke tests for the directives MCP server's tool logic.

Pure standard library — no network, no pytest required. Run with:

    python test_server.py

Exercises the tool functions directly against a throwaway docs directory,
including the release-blocking guard: path traversal must be rejected.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Point DOCS_DIR at a temp docs dir BEFORE importing the server module,
# because server.py resolves DOCS_DIR at import time.
_TMP = Path(tempfile.mkdtemp(prefix="directives-test-"))
(_TMP / "AGENT.md").write_text(
    "# AGENT.md — Development Directives\n\n"
    "## 4. Modularization (Core Concept)\n"
    "Modules have explicit responsibilities.\n\n"
    "### 4.1 Boundaries\n"
    "boundaries are the architecture\n\n"
    "### 4.2 Communication\n"
    "modules talk through interfaces\n\n"
    "## 7. Git and Commit Discipline\n"
    "No AI co-authorship attribution.\n",
    encoding="utf-8",
)
(_TMP / "CHECKLIST.md").write_text(
    "# Checklist\n\n## Setup\nfirst step\n", encoding="utf-8"
)
os.environ["DOCS_DIR"] = str(_TMP)

import server  # noqa: E402

_failures = 0


def check(name: str, condition: bool) -> None:
    global _failures
    print(("PASS" if condition else "FAIL"), "-", name)
    if not condition:
        _failures += 1


def run() -> int:
    check("get_directives returns AGENT.md", "Development Directives" in server.get_directives())

    docs = server.list_documents()
    check("list_documents shows AGENT.md", "AGENT.md" in docs)
    check("list_documents shows CHECKLIST.md", "CHECKLIST.md" in docs)

    check("get_document reads a named doc", "first step" in server.get_document("CHECKLIST.md"))
    check("get_document tolerates a missing .md suffix", "first step" in server.get_document("CHECKLIST"))
    check("get_document reports a clean miss", "not found" in server.get_document("does-not-exist"))

    check("get_section matches a heading", "co-authorship" in server.get_section("git"))
    check("get_section lists sections on miss", "No section heading" in server.get_section("zzz-none"))

    # Regression: a matched parent section must carry its ### subsections,
    # and must not bleed into unrelated sections.
    sect_mod = server.get_section("modular")
    check(
        "get_section: parent carries its subsections",
        "boundaries are the architecture" in sect_mod
        and "modules talk through interfaces" in sect_mod,
    )
    check("get_section: parent match excludes unrelated section", "co-authorship" not in sect_mod)

    # A query that only matches a child heading stays scoped to that child.
    sect_comm = server.get_section("communication")
    check(
        "get_section: child-only match is scoped to the child",
        "modules talk through interfaces" in sect_comm
        and "boundaries are the architecture" not in sect_comm,
    )

    check("health reports ok", server.health().startswith("ok"))

    # Release-blocking guard: no path may escape DOCS_DIR.
    check("guard: '../server' is rejected", "Invalid document path" in server.get_document("../server"))
    check("guard: absolute path is rejected", "Invalid document path" in server.get_document("/etc/passwd"))

    print()
    if _failures:
        print(f"{_failures} test(s) FAILED")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(run())
