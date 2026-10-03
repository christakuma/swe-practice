"""Show the next hint, and record that it was shown.

**The one use case in the display group that writes**, and the distinction is the
whole reason it is a use case rather than a property on the workbench DTO.
`OpenWorkbench` and `InspectRepository` answer *what does this page look like*;
revealing a hint is something the solver **did**, in the exercise, and the attempt
records it next to the commands they ran. The grade suggestion reads that
record — "passed, but with three of four hints" is a different outcome from
"passed" — so a page that printed every hint at once would make the record describe
something nobody did.

**Strictly in order, and the aggregate is what enforces it.** `Attempt.reveal_next_
hint` hands back `hints[hints_revealed]` and refuses once they run out, so there is
no code path by which hint 4 can be read without hints 1 to 3 having been recorded.
This use case does not pass an index and could not: an endpoint taking one would be
an endpoint a solver can skip to the answer with, and the progression is the thing
being measured.

**No workspace, no provisioner.** A hint is content and a log entry; nothing about
it touches the sandbox. That makes it the one use case here that still works for an
attempt whose workspace has been collected — which is right, because reading the
hint is not something the lost workspace prevents, and loading one more port to
refuse on its behalf would be refusing for a reason that is not true.

**It refuses a finished attempt** rather than handing out a hint to a graded one,
and the refusal comes from the aggregate: `_require_active` is the same guard that
refuses a second submission. A tab left open across a submission is the case, and
the same one every other mutating path in the app has.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import RevealedHint
from practice.application.errors import AttemptNotFoundError, ExerciseNotFoundError

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import AttemptRepository, Clock, ContentRepository

__all__ = ["RevealHint"]


@dataclass(frozen=True, slots=True)
class RevealHint:
    """Reveal the next hint for an attempt and persist the event."""

    content: ContentRepository
    attempts: AttemptRepository
    clock: Clock

    def __call__(self, attempt_id: AttemptId) -> RevealedHint:
        """Raises `PolicyViolationError` when the exercise has no hints left."""
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library"
            )

        # The hints come from the attempt's *policy*, copied in when it started, not
        # from the exercise as the library has it now (§4.3). An exercise edited
        # mid-attempt would otherwise reveal a hint the solver's first three do not
        # lead to -- and the log would record a position in a list that no longer
        # exists.
        index = attempt.hints_revealed
        hint = attempt.reveal_next_hint(at=self.clock.now())
        self.attempts.save(attempt)

        return RevealedHint(attempt=attempt, exercise=exercise, hint=hint, index=index)
