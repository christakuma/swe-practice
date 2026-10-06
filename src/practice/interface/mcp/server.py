"""The MCP server: an open attempt, readable by a model, and nothing else.

A third driving adapter over the same use cases as the web app and the CLI,
which is the claim PLAN.md §2 made about the second one and this is the first
test of since: if the tutor context were secretly shaped for a template, a
protocol with no HTML in it would not be able to serve it. Phase 19; ADR 0024.

**What it adds over the copy button is that the answer is live.** A pasted
bundle is a snapshot, stale the moment another command runs. A client attached
here calls `get_context` again and is told what the repository looks like *now*,
and can ask for one file's contents instead of having the solver paste them.

**Three tools, and every one of them reads.** `list_attempts`, `get_context` and
`read_file` are backed by `ListOpenAttempts`, `ExportTutorContext` and
`ReadAttemptFile` -- none of which holds a clock, a grader or a route to
`Workspace.run`. So "the tutor cannot touch your repository" is not a promise
this module keeps by being careful; there is no use case on `Services` it could
call that would. Each tool also carries the protocol's read-only annotation,
which is the same fact said in the vocabulary a client can act on.

**No tool runs a command, deliberately.** It was the obvious fourth one. A
command the model ran would land in the attempt's log, count against the
solver's budget, and be read by the advisory checks and the grade suggestion as
something the *solver* did -- so the tool would be grading a person on a
program's choices. A tutor that wants something run says so, and the solver
runs it.

**The spoiler boundary is inherited, not restated.** Nothing here decides what a
model may be told: `get_context` renders whatever `ExportTutorContext` built,
which has no field for an unrevealed hint, and `read_file` refuses a kata's
hidden suite inside the use case. An open interview is refused by both, through
the attempt's own policy. A fourth surface that re-implemented any of that
would be the one that got it wrong.

**A refusal is a sentence the model can read.** The application and domain
errors are written to be read -- "interview mode withholds the tutor until this
attempt is finished" -- so they are re-raised as `ToolError`, which the SDK
returns as a failed tool call carrying the message. Anything else is a crash,
and the SDK reports it as one without the traceback.

**The only module in the package that imports the SDK**, and
`tests/unit/test_architecture.py` holds that. `mcp` is an optional extra
(`pyproject.toml` says why), so everything that touches it is behind one import
that `practice mcp` defers and can explain the absence of.

**stdio only.** The SDK can also serve HTTP, and this never asks it to: a
listening port would need the whole of `interface/web/security.py` argued over
again for a second server, to reach a client that is already on this machine.
"""

from __future__ import annotations

from importlib.metadata import version
from typing import TYPE_CHECKING, Final

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from practice.application.errors import ApplicationError
from practice.application.tutor import render_markdown
from practice.domain.errors import DomainError
from practice.domain.ids import AttemptId

if TYPE_CHECKING:
    from practice.application.dto import OpenAttempt
    from practice.composition import Services

__all__ = ["SERVER_INSTRUCTIONS", "SERVER_NAME", "build_server"]

SERVER_NAME: Final = "swe-practice"

#: What a client is told once, when it connects. About the *tools*, not about
#: tutoring: the rules for that are the prompt at the top of every context, so
#: they arrive with the thing they govern and cannot drift from the copy button.
SERVER_INSTRUCTIONS: Final = """\
This server exposes the practice exercise the user is working on right now, \
read-only.

- Call get_context before answering anything about their attempt. It returns \
the task, every command they ran with its output, the hints they have revealed \
and the current state of their repository or solution file.
- It is a snapshot. Call it again whenever the user says they ran or changed \
something.
- The context begins with instructions on how to tutor. Follow them: the user \
is here to learn to do this themselves.
- Use read_file to look at a file yourself rather than asking them to paste \
it. For a git exercise you may pass a revision.
- You cannot run commands or change anything here. If something needs \
running, say what and why, and let them run it."""

#: Said of every tool, because it is true of every tool. `open_world_hint` is
#: false because nothing here reaches past this machine.
_READ_ONLY: Final = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def build_server(services: Services) -> MCPServer:
    """The server, closed over the services it reads. Starts nothing.

    Built by function over an already-wired graph, like every router in
    `interface/web/routes/` and for the same reason: there is one place that
    decides which adapters are real, and it is not here. It is also what lets
    a test hand this fakes and connect a client to it in-process.
    """
    server = MCPServer(
        SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        version=version("swe-practice"),
    )

    def resolve(attempt_id: str | None) -> AttemptId:
        """The attempt a tool call is about, or a refusal that says how to pick.

        An id is optional because the ordinary case is one open attempt and a
        solver asking about "this". Guessing among several would be worse than
        asking: a tutor confidently describing the wrong repository is the
        failure this exists to prevent.
        """
        if attempt_id is not None:
            return AttemptId.parse(attempt_id)
        attempts = services.list_open_attempts()
        if not attempts:
            raise ToolError(
                "no attempt is open. Start an exercise in the practice app first; "
                "for a post-mortem on a finished attempt, pass its id, which is "
                "in the workbench URL."
            )
        if len(attempts) > 1:
            listing = "\n".join(_describe(found) for found in attempts)
            raise ToolError(
                f"{len(attempts)} attempts are open, so say which one by passing "
                f"attempt_id:\n{listing}"
            )
        return attempts[0].attempt.id

    @server.tool(annotations=_READ_ONLY, structured_output=False)
    def list_attempts() -> str:
        """List the practice attempts that are open right now, with their ids.

        Use this when get_context says more than one attempt is open, or when
        the user refers to an exercise by name.
        """
        attempts = services.list_open_attempts()
        if not attempts:
            return "No attempt is open."
        return "\n".join(_describe(found) for found in attempts)

    @server.tool(annotations=_READ_ONLY, structured_output=False)
    def get_context(attempt_id: str | None = None) -> str:
        """Get the user's practice attempt as it stands right now.

        Returns the task, every command they ran with its output, the hints
        they revealed, and the current repository state or solution file, under
        instructions on how to tutor. Omit attempt_id when one attempt is open.
        Pass the id of a finished attempt to get its verdict and the author's
        notes for a post-mortem. This is a snapshot: call it again after the
        user runs something.
        """
        try:
            return render_markdown(services.export_tutor_context(resolve(attempt_id)))
        except (ApplicationError, DomainError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(annotations=_READ_ONLY, structured_output=False)
    def read_file(
        path: str, attempt_id: str | None = None, rev: str | None = None
    ) -> str:
        """Read one file from the workspace of the user's open attempt.

        For a git exercise, path is relative to the repository root, and rev
        (for example HEAD, HEAD~1 or origin/main) reads the committed copy at
        that revision instead of the working tree's. For a kata or a SQL drill
        only the user's own solution file can be read.
        """
        try:
            text = services.read_attempt_file(resolve(attempt_id), path, rev=rev)
        except (ApplicationError, DomainError) as exc:
            raise ToolError(str(exc)) from exc
        if text is None:
            where = f"at {rev}" if rev is not None else "in the working tree"
            raise ToolError(f"there is no readable file {path!r} {where}")
        return text

    @server.prompt()
    def tutor(attempt_id: str | None = None) -> str:
        """Start a tutoring conversation about the user's practice attempt."""
        try:
            return render_markdown(services.export_tutor_context(resolve(attempt_id)))
        except (ApplicationError, DomainError) as exc:
            raise ToolError(str(exc)) from exc

    return server


def _describe(found: OpenAttempt) -> str:
    """One open attempt on one line, with the id first because it is the handle.

    The full uuid, as `practice attempts` prints it and for the same reason:
    the use cases take one, and a prefix would need a lookup nothing else
    wants (PLAN.md §13).
    """
    attempt = found.attempt
    notes = [
        f"{attempt.command_count} commands run",
        f"{attempt.hints_revealed} hints revealed",
    ]
    if attempt.policy.is_interview:
        notes.append("interview: no tutor until it is finished")
    if not found.workspace_on_disk:
        notes.append("workspace no longer on disk")
    return f"{attempt.id}  {found.label} ({', '.join(notes)})"
