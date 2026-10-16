"""Run a kata's examples against the solver's source, and record nothing.

The "Run" half of LeetCode's *Run* and *Submit* (ADR 0029). The examples on the
page are the cases a solver can already read, so running against them answers
"does my code do what I think?" without spending a submission and without
touching the hidden suite -- which stays the thing that decides.

**Nothing is persisted, and nothing is graded.** Not a `SolutionSaved`, not a
verdict, not a failed submission. ADR 0013 settled what the log is for when
it refused to append one event per editor save -- *things the solver did in the
exercise* -- and a run sits on the keystroke side of that line: it can be
pressed twenty times while working something out, and a log that held all
twenty would make `latest_source` mean "whatever was last run" and give the
grade suggestion a new kind of entry to learn to ignore. What the solver
submits is still the only source the attempt remembers.

**Refused for a finished attempt**, and refused before the workspace is
reached -- the ordering `SubmitSolution` documents, for the reason it gives: a
completed attempt's workspace has been disposed of, and `attach` would answer
with *the workspace is gone, abandon it*, which is the wrong sentence about an
attempt that passed.

**A kata only.** A git scenario has a console, which already runs whatever the
solver types; a SQL drill has no examples to run. Both are refused by name
rather than with an empty trial, because a Run button that ran nothing would
look like a pass.

**Allowed under interview mode.** The examples are on the page in both modes
(ADR 0027), and running your code against a case the interviewer handed you is
part of an interview rather than help with it -- which is the test ADR 0020
applies to every affordance it withdraws.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    UnsupportedExerciseKindError,
    WorkspaceGoneError,
)
from practice.domain.errors import AttemptStateError
from practice.domain.exercise import KataSpec

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        ExampleRunner,
        SandboxProvisioner,
    )
    from practice.domain.trial import Trial

__all__ = ["TryExamples"]


@dataclass(frozen=True, slots=True)
class TryExamples:
    """The examples, run against a source that nothing remembers."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    examples: ExampleRunner

    def __call__(self, attempt_id: AttemptId, source: str) -> Trial:
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
        if not attempt.is_active:
            raise AttemptStateError(
                f"cannot run: attempt {attempt.id.short} is {attempt.status.value}"
            )

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library"
            )
        spec = exercise.spec
        if not isinstance(spec, KataSpec) or not spec.examples:
            raise UnsupportedExerciseKindError(
                f"{exercise.id} has no examples to run; submit it to have it graded"
            )

        workspace = self.provisioner.attach(exercise, attempt_id)
        if workspace is None:
            raise WorkspaceGoneError(
                f"the workspace for attempt {attempt.id.short} is no longer on "
                f"disk, so nothing can run in it; abandon it and start again"
            )

        return self.examples.run(exercise, workspace, source)
