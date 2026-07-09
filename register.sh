#!/usr/bin/env bash
# Register the directives MCP server with Claude Code (macOS / Linux / Git Bash).
# User scope => available in EVERY project on this machine.
set -euo pipefail

claude mcp add --transport http --scope user directives http://127.0.0.1:49721/mcp
echo
claude mcp list
echo
echo "Registered. In a Claude Code session run /mcp to confirm the tools are visible."
