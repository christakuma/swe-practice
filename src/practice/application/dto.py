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
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from practice.domain.ports import Workspace
    from practice.domain.verdict import Outcome, Verdict

__all__ = ["StartedAttempt", "Submission"]


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
