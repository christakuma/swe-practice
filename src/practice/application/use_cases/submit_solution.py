"""Submit a kata: save the source, grade it, close the attempt, free the disk.

The second half of the vertical slice, and the only use case that touches all
six ports at once. Three decisions in it are worth stating.

**It re-attaches the workspace instead of being handed one.** The caller may be
a different process from the one that started the attempt — a web request, a
second CLI invocation — so taking a live `Workspace` as an argument would make
the use case usable from exactly one place. `attach` reopens what is on disk
without re-running the fixture, which is the resume half of PLAN.md §8.1; a
caller that already holds the handle loses nothing by it.

**The workspace is disposed only on success.** Not in a `finally`: if grading
raises, the attempt is still `ACTIVE`, and §8.1 ties workspace lifetime to
exactly that. Deleting it on the way out of a failed grading pass would destroy
the one thing that could be inspected to find out why, and leave an active
attempt that can never be submitted or resumed.

**The source is saved to the attempt before it is graded**, so the event log
records what was submitted even if grading then fails. A verdict is derived from
something persisted and replayable, never from an argument that was only ever in
memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import Submission
from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)

if TYPE_CHECKING:
    from practice.application.registry import GraderRegistry
    from practice.domain.attempt import ComplexityClaim
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        SandboxProvisioner,
    )

__all__ = ["SubmitSolution"]


@dataclass(frozen=True, slots=True)
class SubmitSolution:
    """Grade a solver's source against the exercise and complete the attempt."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    graders: GraderRegistry
    clock: Clock

    def __call__(
        self,
        attempt_id: AttemptId,
        source: str,
        *,
        complexity: ComplexityClaim | None = None,
    ) -> Submission:
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            # The library changed under a live attempt: an exercise was renamed
            # or removed while someone was working on it. Rare, and worth a
            # distinct error rather than a crash, because the attempt is now
            # ungradable and the only honest thing to do with it is abandon it.
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library"
            )

        grader = self.graders.for_exercise(exercise)
        workspace = self.provisioner.attach(exercise, attempt_id)
        if workspace is None:
            raise WorkspaceGoneError(
                f"the workspace for attempt {attempt.id.short} is no longer on "
                f"disk, so it cannot be graded; abandon it and start again"
            )

        # `declare_complexity` before `save_solution` would also work; this
        # order means the log reads in the order things happened, since the
        # claim is made in the same submission as the source.
        attempt.save_solution(source, at=self.clock.now())
        if complexity is not None:
            attempt.declare_complexity(complexity)

        verdict = grader.grade(exercise, workspace, attempt)
        attempt.complete(verdict, at=self.clock.now())
        self.attempts.save(attempt)

        # Only now, and only on this path: see the module docstring.
        workspace.dispose()

        return Submission(attempt=attempt, exercise=exercise, verdict=verdict)
