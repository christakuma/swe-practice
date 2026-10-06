"""A tutor attached over real stdio, watching an attempt change. Phase 19's exit.

`practice mcp` is started as a subprocess and spoken to by the SDK's own client
over its stdin and stdout, which is exactly what Claude Desktop or Claude Code
does with it. Everything in `tests/integration/test_mcp_server.py` uses the
in-memory transport and one process; this is the only test of the two things
that cannot show:

**Two processes, one attempt.** The server is a different process from the one
the solver is working in, and it holds nothing between calls -- each tool call
reads the database and the repository again. So a command run *here*, in the
test's own process, the way the workbench would run it, has to be in the next
answer the server gives. That is the whole of what makes this better than the
copy button, and a server that cached its first reading would pass every other
test in the phase.

**And the command itself**: that `practice mcp` writes nothing to stdout but the
protocol, on the platform where that is hardest. A stray banner, or text-mode
newline translation on Windows, breaks the framing and the handshake below
never completes.

One test, like the other journeys, and the move in it is the flagship
scenario's tempting wrong one for the reason `test_ask_for_help_mid_scenario`
gives: after `git reset --hard HEAD~1` the published commit is reachable only
from `origin/main`, which is the moment somebody asks a tutor what happened.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import anyio
from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, TextContent

from practice.application.tutor import TUTOR_PROMPT
from practice.composition import build_services
from practice.config import content_root
from practice.domain.ids import ExerciseId
from practice.interface.mcp import SERVER_NAME

if TYPE_CHECKING:
    from pathlib import Path

REVERT = ExerciseId("git/revert-a-pushed-commit")

BAD_COMMIT = "Rename parse_line to parse"

#: The CLI, started the way an installed `practice` script starts it, without
#: depending on where the script was installed or what it is called on this
#: platform.
LAUNCH = "from practice.interface.cli.main import app; app()"


def text_of(result: CallToolResult) -> str:
    assert not result.is_error, result.content
    (block,) = result.content
    assert isinstance(block, TextContent)
    return block.text


def test_a_client_over_stdio_sees_the_attempt_change_and_changes_nothing(
    tmp_path: Path,
) -> None:
    workspaces, database = tmp_path / "ws", tmp_path / "practice.db"
    services = build_services(
        content=content_root(), workspaces=workspaces, database=database
    )
    attempt = services.start_attempt(REVERT).attempt.id

    server = StdioServerParameters(
        command=sys.executable,
        args=[
            "-c",
            LAUNCH,
            "mcp",
            "--content-root",
            str(content_root()),
            "--workspace-root",
            str(workspaces),
            "--database",
            str(database),
        ],
    )

    async def conversation() -> tuple[str, str, str, str, str]:
        async with Client(server) as client:
            assert client.server_info is not None
            assert client.server_info.name == SERVER_NAME

            # One attempt is open, so "this" needs no id.
            fresh = text_of(await client.call_tool("get_context", {}))

            # The solver makes the tempting mistake, in *this* process. Blocking
            # on purpose: nothing else is in flight, and it is one git command.
            services.run_scenario_command(attempt, "git reset --hard HEAD~1")

            stranded = text_of(await client.call_tool("get_context", {}))
            mine = text_of(await client.call_tool("read_file", {"path": "parser.py"}))
            theirs = text_of(
                await client.call_tool(
                    "read_file", {"path": "parser.py", "rev": "origin/main"}
                )
            )
            listing = text_of(await client.call_tool("list_attempts", {}))
            return fresh, stranded, mine, theirs, listing

    fresh, stranded, mine, theirs, listing = anyio.run(conversation)

    # Before: the fixture's state, with the bad commit published.
    assert fresh.startswith(TUTOR_PROMPT)
    assert "## What I have done so far\n\nNothing yet." in fresh
    assert f"(HEAD, main, origin/main) {BAD_COMMIT}" in fresh

    # After: the command the other process ran, and the commit it stranded.
    assert "**1.** Ran `git reset --hard 'HEAD~1'` (exit 0)" in stranded
    assert f"(origin/main) {BAD_COMMIT}" in stranded
    assert "(HEAD, main) " in stranded

    # The tutor can see for itself what the two sides hold.
    assert "def parse_line(" in mine
    assert "def parse(" in theirs

    assert f"{attempt}  Undo a commit that is already on origin" in listing
    assert "1 commands run" in listing

    # Nothing survives the wire that was not text: no carriage return crept in.
    assert "\r" not in stranded

    # And five tool calls later the attempt holds the one command the solver
    # ran, and the repository is where that command left it.
    stored = services.attempts.get(attempt)
    assert stored is not None
    assert [run.command_line for run in stored.commands] == [
        "git reset --hard 'HEAD~1'"
    ]
    assert len(stored.events) == 1
    view = services.inspect_repository(attempt)
    assert view is not None
    assert view.status.is_pristine
    assert (
        view.branches["refs/heads/main"]
        != (view.remote_branches["refs/remotes/origin/main"])
    )
