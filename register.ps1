# Register the directives MCP server with Claude Code (Windows / PowerShell).
# User scope => available in EVERY project on this machine.
$ErrorActionPreference = "Stop"

claude mcp add --transport http --scope user directives http://127.0.0.1:49721/mcp
Write-Host ""
claude mcp list
Write-Host ""
Write-Host "Registered. In a Claude Code session run /mcp to confirm the tools are visible."
