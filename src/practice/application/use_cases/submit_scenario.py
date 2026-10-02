"""Submit a git scenario: grade the repository as the solver left it, close the attempt.

The other half of the scenario slice, and deliberately a separate use case from
`SubmitSolution` rather than a flag on it. They share a shape — attach, grade,
complete, save, dispose — and almost nothing else: a kata submission carries source
to be saved into the event log before grading, and a scenario carries nothing at all,
because the thing being graded is already on disk and the log already holds every
command that put it there.

The three orderings `SubmitSolution` documents hold here for the same reasons, and
one of them is load-bearing in a way it is not for a kata:

**The workspace is disposed only on success, never in a `finally`.** If grading
raises, the attempt is still `ACTIVE`, and PLAN.md §8.1 ties workspace lifetime to
exactly that. For a kata the cost of getting this wrong is a lost pytest run; for a
scenario it is a repository the solver spent twenty commands building, and the only
artifact that could explain why grading failed.

**It re-attaches rather than being handed a workspace**, so the use case works from a
process that did not start the attempt — a web request, a second CLI invocation.

**A finished attempt is refused before the workspace is reached.** A successful
submission disposes of the workspace, so without this guard a double-clicked submit
button reached `attach`, got nothing, and was told the workspace was gone and to
*abandon the attempt and start again* -- about an attempt that had just been graded
successfully. `Attempt.complete` refuses a second call too, with the right message,
but only after `attach` had already produced the wrong one. The same guard is in
`RunScenarioCommand` and, as of this phase, in `SubmitSolution`.

**There is nothing to save before grading.** Which is worth stating rather than
leaving as an absence: the equivalent guarantee is already met, because
`RunScenarioCommand` recorded every command as it ran. A verdict here is still
derived from something persisted and replayable; the persisting just happened
earlier.
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
from practice.domain.errors import AttemptStateError

if TYPE_CHECKING:
    from practice.application.registry import GraderRegistry
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        SandboxProvisioner,
    )

__all__ = ["SubmitScenario"]


@dataclass(frozen=True, slots=True)
class SubmitScenario:
    """Grade an attempt's repository against its exercise and complete the attempt."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    graders: GraderRegistry
    clock: Clock

    def __call__(self, attempt_id: AttemptId) -> Submission:
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
        if not attempt.is_active:
            raise AttemptStateError(
                f"cannot submit: attempt {attempt.id.short} is {attempt.status.value}"
            )

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            # The library changed under a live attempt: an exercise was renamed
            # or removed while someone was working on it. The attempt is now
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

        verdict = grader.grade(exercise, workspace, attempt)
        attempt.complete(verdict, at=self.clock.now())
        self.attempts.save(attempt)

        # Only now, and only on this path: see the module docstring.
        workspace.dispose()

        return Submission(attempt=attempt, exercise=exercise, verdict=verdict)
