# Directives MCP Server

A tiny MCP (Model Context Protocol) server that serves your engineering
directives (`AGENT.md` and any other markdown documents) to **every Claude
Code instance on your machine**, from a single Docker container on an
uncommon local port.

Register it once with user scope; after that, any Claude Code session in any
project can call `get_directives` and work under your rules — no copying
files between repositories.

## How it fits together

```
┌─────────────────────────┐
│ Docker: directives-mcp  │  serves ./docs/*.md via MCP
│ 127.0.0.1:49721/mcp     │  (streamable HTTP transport)
└───────────▲─────────────┘
            │ registered once: claude mcp add --scope user
┌───────────┴─────────────┐
│ Any Claude Code session │  tools: get_directives, get_section,
│ in any project          │         get_document, list_documents, health
└─────────────────────────┘
```

## Project layout

```
directives-mcp-server/
├── server.py            # the MCP server (FastMCP, streamable-HTTP)
├── requirements.txt     # pinned runtime dependency (mcp)
├── pyproject.toml       # project metadata + ruff config
├── Dockerfile           # slim, non-root image
├── docker-compose.yml   # one-command build + run, localhost-only
├── .dockerignore        # keeps the build context minimal
├── .gitignore
├── docs/
│   └── AGENT.md         # THE served directives — single source of truth
├── test_server.py       # offline smoke tests of the tool logic
├── verify_client.py     # end-to-end MCP reachability check
├── register.ps1         # register with Claude Code (Windows)
└── register.sh          # register with Claude Code (macOS/Linux/Git Bash)
```

## Setup (one time)

```bash
# 1. Build and start the container
docker compose up -d --build

# 2. Register with Claude Code — user scope = available in ALL projects
#    (or run ./register.sh  /  ./register.ps1)
claude mcp add --transport http --scope user directives http://127.0.0.1:49721/mcp

# 3. Verify Claude Code can reach it
claude mcp list          # directives should show ✓ Connected
```

Inside any Claude Code session you can also run `/mcp` to confirm the server
and its tools are visible. Newly added servers are picked up when a session
starts, so restart Claude Code (or start a new session) after registering.

## Tools exposed

| Tool | Purpose |
|---|---|
| `get_directives()` | Returns the full master `AGENT.md` |
| `get_section(query, document?)` | Returns section(s) whose heading matches, e.g. `get_section("commit")` |
| `get_document(name)` | Returns any document in `docs/` by name |
| `list_documents()` | Inventory of available documents |
| `health()` | Liveness check |

## Verifying it works

```bash
# Offline unit tests of the tool logic (runs in the built image, no network):
docker run --rm -v "$PWD:/work" -w /work --entrypoint python \
  directives-mcp:latest test_server.py

# End-to-end: connect over MCP and list/call the tools.
# From another container against the published port:
docker run --rm --network host -v "$PWD:/work" -w /work --entrypoint python \
  directives-mcp:latest verify_client.py
```

On Windows/Docker Desktop, reach the host's published port from a container
with `MCP_URL=http://host.docker.internal:49721/mcp`.

## Directing Claude Code to use it

Put this one line in each project's `CLAUDE.md` (this is the entire
per-project footprint):

```markdown
Before any work in this repository, call the `directives` MCP server's
`get_directives` tool and follow the returned document as the authoritative
source for code standards, sprint structure, modularization, commit
discipline, and clarification protocol. Re-read relevant sections with
`get_section` when starting a sprint task.
```

Or just say it in the prompt: *"Load my directives from the directives MCP
server, then execute Sprint 0."*

## Updating your directives

Edit files in `./docs/` — the directory is volume-mounted read-only into the
container, so changes are live immediately. No rebuild, no restart. Add more
documents (e.g. `CHECKLIST.md`, `LARAVEL_MAPPING.md`) by dropping them into
`docs/`; they become available through `get_document` at once.

## Operations

```bash
docker compose logs -f directives    # watch requests
docker compose restart directives    # restart
docker compose down                  # stop
claude mcp remove directives         # unregister from Claude Code
```

## Notes

- Port **49721** is deliberately uncommon and bound to `127.0.0.1` only, so
  the server is unreachable from your network. If you ever want it reachable
  from other machines, change the bind and add an auth header — do not expose
  it unauthenticated.
- The container runs as an unprivileged user (`uid 10001`) and the docs volume
  is mounted read-only.
- The `--scope user` registration lives in `~/.claude.json`, so it applies to
  every project without touching any repo. Use `--scope project` instead if
  you want a specific repo to carry the registration in a committable
  `.mcp.json`.
