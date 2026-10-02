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
    from practice.domain.ports import Workspace, WorkspaceSummary
    from practice.domain.verdict import Outcome, Verdict

__all__ = [
    "Abandoned",
    "Collection",
    "OpenAttempt",
    "RanCommand",
    "StartedAttempt",
    "Submission",
    "WorkspaceState",
]


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


@dataclass(frozen=True, slots=True)
class OpenAttempt:
    """One attempt still in flight, and the two facts a prompt needs about it.

    `exercise` is optional where every other DTO's is not, and that is the honest
    encoding rather than a convenience: an exercise can be renamed or deleted from
    the library under a live attempt, and the resulting attempt is one that can be
    *abandoned* and never graded. A listing that refused to show it would hide the
    only thing that can be done about it.

    `workspace_on_disk` is what separates the two offers. An attempt whose workspace
    has been collected cannot be resumed, so a prompt that did not know this would
    offer a choice that cannot be taken.
    """

    attempt: Attempt
    exercise: Exercise | None
    workspace_on_disk: bool

    @property
    def label(self) -> str:
        """The exercise's title, or its id when the library no longer has it."""
        if self.exercise is None:
            return f"{self.attempt.exercise_id} (no longer in the library)"
        return self.exercise.title

    @property
    def can_resume(self) -> bool:
        return self.workspace_on_disk and self.exercise is not None


@dataclass(frozen=True, slots=True)
class Abandoned:
    """An attempt given up on, and the workspace that went with it.

    Carries the attempt so a caller can report when it started and how far it got
    -- the log survives, which is the difference between abandoning an attempt and
    deleting its row.
    """

    attempt: Attempt
    exercise: Exercise | None


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    """One workspace on disk, and whether an active attempt still owns it.

    The orphan rule of PLAN.md 8.1, as a value: `in_use` is the join against the
    attempt table, and everything else is what the provisioner found.
    """

    workspace: WorkspaceSummary
    in_use: bool

    @property
    def is_orphan(self) -> bool:
        """A workspace with no corresponding `active` attempt row. Collectable."""
        return not self.in_use


@dataclass(frozen=True, slots=True)
class Collection:
    """What `practice gc` found, and what it did about it.

    The same classification whether or not anything was deleted, so a dry run and a
    real one cannot disagree about what counts as an orphan -- which is the bug that
    makes a destructive command untrustworthy.
    """

    workspaces: tuple[WorkspaceState, ...]
    deleted: tuple[str, ...]

    @property
    def orphans(self) -> tuple[WorkspaceState, ...]:
        return tuple(state for state in self.workspaces if state.is_orphan)

    @property
    def in_use(self) -> tuple[WorkspaceState, ...]:
        return tuple(state for state in self.workspaces if state.in_use)

    @property
    def total_bytes(self) -> int:
        return sum(state.workspace.size_bytes for state in self.workspaces)

    @property
    def reclaimable_bytes(self) -> int:
        """What collecting would free, which is the number worth printing."""
        return sum(state.workspace.size_bytes for state in self.orphans)
