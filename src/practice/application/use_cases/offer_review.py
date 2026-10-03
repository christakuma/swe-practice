"""What the tool would grade this attempt, and whether it still can.

The read half of the review pair, and a read in the sense `OpenWorkbench` is one:
nothing here writes. It exists because the panel a solver schedules from has to
show three things no single port answers — the attempt's verdict, the card as the
store currently has it, and the grade the suggestion rule reads off the two — and
a route assembling those itself would be the place where the buttons shown and
the post accepted come apart.

**It refuses an attempt with no verdict rather than suggesting something.** A
suggestion needs a verdict, an elapsed time that has stopped running and a hint
count that is final; an active attempt has none of those, and a number that
changed every time the page was refreshed would be worse than no number. The
refusal is `AttemptStateError`, which is what `suggest_grade` raises for the same
reason — raised here first so the message names the attempt rather than the rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import ReviewOffer
from practice.application.errors import AttemptNotFoundError, ExerciseNotFoundError
from practice.domain.errors import AttemptStateError
from practice.domain.scheduling import suggest_grade

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        ReviewRepository,
    )

__all__ = ["OfferReview", "load_offer"]


@dataclass(frozen=True, slots=True)
class OfferReview:
    """The review a finished attempt is eligible for, if it still is."""

    content: ContentRepository
    attempts: AttemptRepository
    reviews: ReviewRepository

    def __call__(self, attempt_id: AttemptId) -> ReviewOffer:
        return load_offer(
            attempt_id,
            content=self.content,
            attempts=self.attempts,
            reviews=self.reviews,
        )


def load_offer(
    attempt_id: AttemptId,
    *,
    content: ContentRepository,
    attempts: AttemptRepository,
    reviews: ReviewRepository,
) -> ReviewOffer:
    """The join, as a function, because `GradeReview` needs exactly the same one.

    **A shared function rather than one use case calling the other.** `GradeReview`
    has to know whether the attempt has already been reviewed before it writes, and
    that is the question `ReviewOffer.already_reviewed` answers — so the two either
    share this or come to disagree about which attempts are still open. A use case
    holding a use case would have given the same result and put a second decision
    in the composition root about which one owns the repositories.
    """
    attempt = attempts.get(attempt_id)
    if attempt is None:
        raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
    if attempt.verdict is None:
        raise AttemptStateError(
            f"cannot review attempt {attempt.id.short}: it is "
            f"{attempt.status.value} and has no verdict to grade"
        )

    exercise = content.get(attempt.exercise_id)
    if exercise is None:
        raise ExerciseNotFoundError(
            f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
            f"no longer in the library"
        )

    return ReviewOffer(
        attempt=attempt,
        exercise=exercise,
        card=reviews.get_card(attempt.exercise_id),
        suggestion=suggest_grade(attempt, exercise),
    )
