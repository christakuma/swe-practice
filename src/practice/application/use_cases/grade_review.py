"""Move the card: the one thing in Phase 9 that writes.

The use case `use_cases/__init__.py` has been naming since Phase 8. It takes a
finished attempt and a grade, runs the grade through the `Scheduler`, and stores
the card that comes back — which is the whole of what turns a pile of verdicts
into a queue.

**The grade is optional, and that is the suggestion's entire delivery
mechanism.** `grade=None` means *use what the tool read off the attempt*, so a
surface that offers one button and a surface that offers four reach the same use
case, and the suggestion is never computed twice or differently. What comes back
says which was used (`Reviewed.followed_the_suggestion`), because an override is
the only feedback the suggestion rule will ever get.

**A card is created here and nowhere else.** `ReviewRepository.get_card` returns
`None` for an exercise never scheduled and deliberately does not invent one — it
has no clock, and a repository manufacturing domain objects would make "has this
ever been reviewed?" unanswerable. This has a clock, so `ReviewCard.new` is its
call to make.

**One attempt moves a card once.** The guard is `ReviewOffer.already_reviewed`,
shared with the panel that decides whether to show the buttons, so the two cannot
disagree. Without it a double-click, a refresh, or a tab left open would advance
the interval twice for one piece of evidence — and a card is replaced rather than
versioned (`sqlite/reviews.py`), so there would be nothing to undo it from. It is
the same shape of guard `Attempt.complete` applies to a second submission, for
the same reason, one layer out: the aggregate cannot enforce this one, because
the thing being written is not the attempt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import Reviewed
from practice.application.use_cases.offer_review import load_offer
from practice.domain.errors import AttemptStateError
from practice.domain.review import ReviewCard

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        ReviewRepository,
        Scheduler,
    )
    from practice.domain.review import Grade

__all__ = ["GradeReview"]


@dataclass(frozen=True, slots=True)
class GradeReview:
    """Schedule the next sighting of an exercise, from one finished attempt."""

    content: ContentRepository
    attempts: AttemptRepository
    reviews: ReviewRepository
    scheduler: Scheduler
    clock: Clock

    def __call__(self, attempt_id: AttemptId, grade: Grade | None = None) -> Reviewed:
        """Raises `AttemptStateError` for an attempt already reviewed or unfinished."""
        offer = load_offer(
            attempt_id,
            content=self.content,
            attempts=self.attempts,
            reviews=self.reviews,
        )
        if offer.already_reviewed:
            raise AttemptStateError(
                f"attempt {offer.attempt.id.short} has already been reviewed; "
                f"{offer.exercise.id} is next due on "
                f"{offer.card.due_on.isoformat() if offer.card else 'never'}"
            )

        chosen = grade if grade is not None else offer.suggested
        # `clock.today()` and not `clock.now().date()`: the clock is the one that
        # decides what day it is, and a card created on one reading and scheduled
        # on another is the asymmetry the `Scheduler` port was reshaped to avoid.
        before = offer.card or ReviewCard.new(offer.exercise.id, self.clock.today())
        card = self.scheduler.next_card(before, chosen, self.clock.now())
        self.reviews.save_card(card)

        return Reviewed(
            attempt=offer.attempt,
            exercise=offer.exercise,
            card=card,
            grade=chosen,
            suggestion=offer.suggestion,
        )
