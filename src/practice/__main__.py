"""`python -m practice`, which is the `practice` command without the script.

Added for one caller and one reason, found the first time the MCP server was
left running. An MCP client keeps `practice mcp` alive for as long as the client
is open. Started through the `practice` console script, that is a long-lived
process holding `.venv/Scripts/practice.exe` open -- and on Windows an open
executable cannot be replaced. `uv run` re-installs the project whenever
`pyproject.toml` has changed, replacing that script is part of doing so, and so
`uv run practice up` failed with *"the process cannot access the file because
it is being used by another process"* for as long as any AI client was running.

The earlier advice was `uv run --no-sync` in the client's configuration, which
was aimed at the opposite collision -- the server's own launch disturbing a
running `practice up` -- and did nothing about this one.

Run this way, the long-lived process is the interpreter, which a sync does not
replace, and the script is never opened at all. So a client is configured with
`.venv/Scripts/python -m practice mcp`, and `uv run` is free to rebuild
underneath it.

Nothing else should need this. A person types `practice`.
"""

from practice.interface.cli.main import app

app()
