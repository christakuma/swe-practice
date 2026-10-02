"""What a use case hands back.

Thin on purpose. These carry domain objects rather than flattening them into
display strings, because two very different adapters read them — a Typer command
and a Jinja template — and whichever one formatted first would end up owning the
formatting for the other.

What they *do* add is the join. A caller holding an `Attempt` has an
`ExerciseId` and not an `Exercise`, so rendering anything at all means another
trip to the content repository; returning both together is what stops every
route and every command from making that trip itself and disagreeing about what
to do when it misses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from practice.domain.attempt import Attempt, CommandRun
    from practice.domain.exercise import Exercise
    from practice.domain.ports import Workspace
    from practice.domain.verdict import Outcome, Verdict

__all__ = ["RanCommand", "StartedAttempt", "Submission"]


@dataclass(frozen=True, slots=True)
class StartedAttempt:
    """A provisioned attempt, ready to be worked on.

    The `Workspace` is included because the caller that started the attempt is
    usually the one about to write a file into it, and making it attach again to
    get a handle it was just given would be ceremony. A caller in a *different*
    process — the web app, a second CLI invocation — goes through
    `SandboxProvisioner.attach` instead, which is why nothing downstream of this
    assumes the object is still live.
    """

    attempt: Attempt
    exercise: Exercise
    workspace: Workspace

    @property
    def prompt(self) -> str:
        return self.exercise.prompt


@dataclass(frozen=True, slots=True)
class Submission:
    """A graded, completed attempt."""

    attempt: Attempt
    exercise: Exercise
    verdict: Verdict

    @property
    def outcome(self) -> Outcome:
        """Derived by the verdict, never stored — see `Verdict.outcome`."""
        return self.verdict.outcome

    @property
    def passed(self) -> bool:
        """True for a pass with advisories too: the goal was met either way."""
        return self.verdict.passed


@dataclass(frozen=True, slots=True)
class RanCommand:
    """One command, as the attempt now remembers it.

    The `CommandRun` rather than the bare `CommandResult`, because the caller wants
    the things only the aggregate knows: when it happened, and the normalised line it
    was recorded as. The attempt comes with it so a console can redraw its budget
    without a second lookup -- `remaining_commands` is the number a solver watches.
    """

    attempt: Attempt
    exercise: Exercise
    command: CommandRun

    @property
    def remaining_commands(self) -> int:
        return self.attempt.remaining_commands

    @property
    def succeeded(self) -> bool:
        """A failing command is a normal outcome, often the instructive one."""
        return self.command.result.succeeded
