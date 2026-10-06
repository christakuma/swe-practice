"""The MCP server: a third driving adapter, over the read side only.

Importing this package imports the `mcp` SDK, which is an optional extra. That
is deliberate and it is the only place it happens: `practice mcp` defers this
import so the rest of the CLI loads on a base install, and turns its absence
into an instruction.

Not to be confused with the SDK's own top-level `mcp` package. This is
`practice.interface.mcp`, and inside it `from mcp.server import ...` is an
absolute import of theirs.
"""

from practice.interface.mcp.server import (
    SERVER_INSTRUCTIONS,
    SERVER_NAME,
    build_server,
)

__all__ = ["SERVER_INSTRUCTIONS", "SERVER_NAME", "build_server"]
