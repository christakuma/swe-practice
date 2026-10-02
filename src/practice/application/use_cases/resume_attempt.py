"""Pick up an attempt a previous process started.

The use case the attempt table exists for, and the shortest one in the system —
which is the point. Resuming is a *read*: load the aggregate, find the workspace it
left on disk, hand both back. Nothing is written, no timestamp is taken, and the
attempt's status does not change, because nothing about it has happened yet.

That is worth stating because the obvious alternative is to record a `resumed`
event. It was considered and rejected: an event in the log is something the solver
did, and the process assertions in PLAN.md §6.3 read that log to decide whether
someone reached for the reflog or force-pushed a shared branch. Opening a session
again is not an action in the exercise, and putting it in the log would mean every
advisory check had to learn to ignore one kind of entry.

**It re-attaches rather than re-provisioning**, which is the half of PLAN.md §8.1
that makes an interrupted session recoverable at all: the workspace of an `ACTIVE`
attempt is still on disk, with the repository exactly as the last command left it.
A provisioner that rebuilt the fixture would hand back a pristine repository and
silently discard twenty commands of work.

**A workspace that is gone is `WorkspaceGoneError`, not a fresh one.** The attempt
can be abandoned but never graded, and the distinction is the whole reason the
status flag exists. Inventing a replacement workspace would make the attempt's log
describe commands that were never run against the repository being graded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import StartedAttempt
from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.errors import AttemptStateError

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        SandboxProvisioner,
    )

__all__ = ["ResumeAttempt"]


@dataclass(frozen=True, slots=True)
class ResumeAttempt:
    """Reopen an active attempt and its workspace. Writes nothing."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner

    def __call__(self, attempt_id: AttemptId) -> StartedAttempt:
        """Returns the same `StartedAttempt` that starting one does.

        Deliberately the same DTO: a caller about to run a command or render a
        workbench needs the attempt, its exercise and its workspace, and whether
        the session is one second or one week old does not change that. A separate
        `ResumedAttempt` type carrying identical fields would make every consumer
        handle two shapes of the same thing.
        """
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
        if not attempt.is_active:
            raise AttemptStateError(
                f"cannot resume: attempt {attempt.id.short} is {attempt.status.value}"
            )

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library; abandon it"
            )

        workspace = self.provisioner.attach(exercise, attempt_id)
        if workspace is None:
            raise WorkspaceGoneError(
                f"the workspace for attempt {attempt.id.short} is no longer on "
                f"disk, so there is nothing to resume; abandon it and start again"
            )

        return StartedAttempt(attempt=attempt, exercise=exercise, workspace=workspace)
