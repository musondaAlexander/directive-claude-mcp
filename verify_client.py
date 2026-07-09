"""
End-to-end reachability check for the directives MCP server.

Connects over the same streamable-HTTP transport Claude Code uses, performs
the MCP handshake, lists the exposed tools, and calls a couple of them.
This is the authoritative proof that "the tools are reachable".

    python verify_client.py                 # uses http://127.0.0.1:49721/mcp
    MCP_URL=http://host:port/mcp python verify_client.py

Exits 0 on success, 1 on failure.
"""

from __future__ import annotations

import os
import sys

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = os.environ.get("MCP_URL", "http://127.0.0.1:49721/mcp")
EXPECTED = {
    "list_documents",
    "get_directives",
    "get_document",
    "get_section",
    "health",
}


async def _run() -> int:
    print(f"connecting to {URL} ...")
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"initialized: server = {init.serverInfo.name} "
                  f"v{init.serverInfo.version}")

            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            print("tools exposed:", ", ".join(sorted(names)))

            missing = EXPECTED - names
            if missing:
                print("MISSING TOOLS:", ", ".join(sorted(missing)))
                return 1

            health = await session.call_tool("health", {})
            print("health() ->", health.content[0].text)

            directives = await session.call_tool("get_directives", {})
            head = directives.content[0].text[:60].replace("\n", " ")
            print("get_directives() ->", head, "...")

    print("\nOK: all expected tools reachable and responding")
    return 0


def main() -> None:
    try:
        code = anyio.run(_run)
    except Exception as exc:  # noqa: BLE001 - surface any transport error clearly
        print(f"FAILED to reach server: {exc!r}")
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
