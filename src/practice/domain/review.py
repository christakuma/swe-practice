"""Spaced-repetition value objects.

The card and its vocabulary only. The SM-2 arithmetic that moves a card lives in
`domain/scheduling/` behind the `Scheduler` port and arrives in Phase 9 — the
card has to exist first, because `ReviewRepository` and `Scheduler` are both
declared in `ports.py` now.

`ease` has a floor of 1.3, which is SM-2's own, and the floor is enforced here
rather than only inside the scheduler: it is the invariant the Phase 9 property
tests assert, and an invariant that only holds while one function is the sole
writer is not an invariant.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from practice.domain.errors import InvalidValueError

if TYPE_CHECKING:
    from datetime import date, datetime

    from practice.domain.ids import ExerciseId

__all__ = [
    "DEFAULT_EASE",
    "MINIMUM_EASE",
    "CardState",
    "Grade",
    "ReviewCard",
]

MINIMUM_EASE: Final = 1.3
DEFAULT_EASE: Final = 2.5


class CardState(StrEnum):
    """Where a card sits in the learning pipeline."""

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    LAPSED = "lapsed"


class Grade(StrEnum):
    """The solver's self-assessment after an attempt, in SM-2's four buckets."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


@dataclass(frozen=True, slots=True)
class ReviewCard:
    """One exercise's scheduling state. Immutable; the scheduler returns a new one."""

    exercise_id: ExerciseId
    due_on: date
    state: CardState = CardState.NEW
    ease: float = DEFAULT_EASE
    interval_days: int = 0
    reps: int = 0
    lapses: int = 0
    last_reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.ease < MINIMUM_EASE:
            raise InvalidValueError(
                f"ease must not drop below {MINIMUM_EASE}, got {self.ease}"
            )
        if self.interval_days < 0:
            raise InvalidValueError("interval_days cannot be negative")
        if self.reps < 0 or self.lapses < 0:
            raise InvalidValueError("reps and lapses cannot be negative")
        if self.last_reviewed_at is not None and self.last_reviewed_at.tzinfo is None:
            raise InvalidValueError("last_reviewed_at must be timezone-aware")

    @classmethod
    def new(cls, exercise_id: ExerciseId, today: date) -> ReviewCard:
        """A card for an exercise never attempted: due immediately."""
        return cls(exercise_id=exercise_id, due_on=today)

    def is_due(self, today: date) -> bool:
        return self.due_on <= today
