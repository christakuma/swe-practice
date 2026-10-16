"""Stop trying: close an attempt on the last submission that failed.

The way out of an attempt that ADR 0029 made necessary. Once a failing verdict
stopped closing an attempt, a solver who could not get there had two exits --
pass, or abandon -- and abandoning is the wrong one for somebody who *tried*.
An abandoned attempt has no verdict, so the progress page does not count it and
the schedule control is never offered for it: three honest failures would leave
no trace in either, and the card for an exercise somebody could not do is the
card spaced repetition most needs to move.

So this completes the attempt with the verdict the solver last got, and from
there it is an ordinary completed failure: `OfferReview` suggests `AGAIN`, and
`summarise` counts it.

**Not a submission.** It grades nothing and runs nothing. The verdict is one
the log already holds, which is why `Attempt.concede` refuses an attempt with
no failed submission rather than asking for a fresh one: a grading pass here
would be a submit button with a different label.

**The row is saved before the workspace is discarded**, for the reason
`AbandonAttempt` gives: a workspace under no active attempt is what `practice
gc` collects, while a deleted workspace under an active one is a session that
can never be resumed. And it discards by directory name for the same reason
too -- it needs no exercise to do it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import Submission
from practice.application.errors import AttemptNotFoundError, ExerciseNotFoundError

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        SandboxProvisioner,
    )

__all__ = ["ConcedeAttempt"]


@dataclass(frozen=True, slots=True)
class ConcedeAttempt:
    """Complete an attempt on its last failed verdict, and free its workspace."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    clock: Clock

    def __call__(self, attempt_id: AttemptId) -> Submission:
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")

        # The aggregate refuses a finished attempt and one with nothing to
        # concede on, in its own words; neither is restated here.
        verdict = attempt.concede(at=self.clock.now())

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            # Checked after `concede` and before `save`, so a refusal leaves the
            # stored attempt untouched. An attempt whose exercise has gone can
            # still be abandoned; a `Submission` needs the exercise it is about.
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library; abandon it instead"
            )

        self.attempts.save(attempt)
        self.provisioner.discard(attempt_id.short)

        return Submission(attempt=attempt, exercise=exercise, verdict=verdict)
