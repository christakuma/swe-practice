"""A scheduler that does one thing, so a use case test can say what it did.

Satisfies `practice.domain.ports.Scheduler`, and it is the second implementation
PLAN.md §13 asks of the port — `Sm2Scheduler` is the first. Without it the port
would be a protocol with one implementation and no double, which §13 says to
delete rather than carry.

**It records the calls and moves the card by a fixed number of days.** Not an
SM-2 re-implementation: a test about `GradeReview` is about which grade reached
the scheduler and whether the returned card was saved, and a double that did the
real arithmetic would make those assertions depend on the arithmetic — so a
change to the intervals would break the use-case tests, which is the wrong place
to find out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from practice.domain.review import CardState, ReviewCard

if TYPE_CHECKING:
    from datetime import datetime

    from practice.domain.review import Grade

__all__ = ["FixedScheduler", "Scheduled"]


@dataclass(frozen=True, slots=True)
class Scheduled:
    """One call, as the double saw it."""

    card: ReviewCard
    grade: Grade
    now: datetime


class FixedScheduler:
    """Pushes every card out by the same interval, whatever the grade."""

    def __init__(self, interval_days: int = 3) -> None:
        self._interval = interval_days
        #: Every call in order, so a test can assert on the grade that arrived
        #: rather than inferring it from the card that came back.
        self.calls: list[Scheduled] = []

    def next_card(self, card: ReviewCard, grade: Grade, now: datetime) -> ReviewCard:
        self.calls.append(Scheduled(card=card, grade=grade, now=now))
        return ReviewCard(
            exercise_id=card.exercise_id,
            due_on=now.date() + timedelta(days=self._interval),
            state=CardState.REVIEW,
            ease=card.ease,
            interval_days=self._interval,
            reps=card.reps + 1,
            lapses=card.lapses,
            last_reviewed_at=now,
        )

    @property
    def grades(self) -> list[Grade]:
        """The grades it was called with, which is what most tests assert on."""
        return [call.grade for call in self.calls]

    def __repr__(self) -> str:
        return f"FixedScheduler({self._interval} days, {len(self.calls)} calls)"
