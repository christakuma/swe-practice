"""Spaced-repetition value objects.

The card and its vocabulary only. The SM-2 arithmetic that moves a card lives in
`domain/scheduling/sm2.py`, behind the `Scheduler` port — the card came first,
in Phase 1, because `ReviewRepository` and `Scheduler` are both declared in
`ports.py` and neither could be written down without it.

`ease` has a floor of 1.3, which is SM-2's own, and the floor is enforced here
rather than only inside the scheduler: it is the invariant the scheduler's
property tests assert, the scheduler is not the sole writer — a repository is —
and an invariant that holds only while one function writes it is not an
invariant. The schema restates it a third time, for the third reason
(`sqlite/migrations/0001_initial.sql`).

**The card carries two schedulers' state, and Phase 13 is why.** ADR 0008
shipped SM-2 with FSRS behind the same port and named the concession exactly:
`ease` and `interval_days` are SM-2's working state, FSRS wants stability and
difficulty instead, and *"an honest migration would add columns rather than
reuse them"*. Phase 13 added the second scheduler and took that option rather
than the cheap one — `stability` and `difficulty` are new and nullable, and
`ease` was left alone.

The alternative, rejected, was to overload `ease` as "whatever the scheduler's
primary number is". It costs nothing to write and it makes every reader of a
card wrong: the floor of 1.3 is SM-2's and means nothing to a difficulty on a
1 to 10 scale, the schema's `CHECK (ease >= 1.3)` would have started refusing valid
FSRS state, and a card written by one scheduler and read by the other would be
silently misinterpreted rather than visibly empty. `has_memory_state` is what
makes that emptiness legible: `None` means *no FSRS has ever touched this card*,
which is a question a second scheduler has to be able to ask about a history the
first one wrote.
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
    "MAXIMUM_DIFFICULTY",
    "MINIMUM_DIFFICULTY",
    "MINIMUM_EASE",
    "CardState",
    "Grade",
    "ReviewCard",
]

MINIMUM_EASE: Final = 1.3
DEFAULT_EASE: Final = 2.5

#: FSRS's difficulty scale, and the bounds every implementation clamps to. Here
#: for the same reason `MINIMUM_EASE` is: the scheduler is not the only writer.
MINIMUM_DIFFICULTY: Final = 1.0
MAXIMUM_DIFFICULTY: Final = 10.0


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
    #: FSRS's half of the vocabulary; see the module docstring. `None` on every
    #: card SM-2 has ever written, which is the whole library until the scheduler
    #: is switched, and which is why neither field has a non-null default.
    stability: float | None = None
    difficulty: float | None = None

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
        # Strictly positive rather than non-negative: stability is a divisor in
        # FSRS's retrievability curve, so a stored zero is not a slightly wrong
        # card but a `ZeroDivisionError` in the next review.
        if self.stability is not None and self.stability <= 0:
            raise InvalidValueError(f"stability must be positive, got {self.stability}")
        if self.difficulty is not None and not (
            MINIMUM_DIFFICULTY <= self.difficulty <= MAXIMUM_DIFFICULTY
        ):
            raise InvalidValueError(
                f"difficulty must be between {MINIMUM_DIFFICULTY} and "
                f"{MAXIMUM_DIFFICULTY}, got {self.difficulty}"
            )
        # One field set and the other not is not a card either scheduler can
        # read: FSRS needs both to move one, and a half-written pair means a
        # mapper or a migration dropped a column rather than that nothing has
        # scheduled this yet.
        if (self.stability is None) != (self.difficulty is None):
            raise InvalidValueError(
                "stability and difficulty are set together or not at all; got "
                f"stability={self.stability!r}, difficulty={self.difficulty!r}"
            )

    @classmethod
    def new(cls, exercise_id: ExerciseId, today: date) -> ReviewCard:
        """A card for an exercise never attempted: due immediately."""
        return cls(exercise_id=exercise_id, due_on=today)

    def is_due(self, today: date) -> bool:
        return self.due_on <= today

    @property
    def has_memory_state(self) -> bool:
        """Whether an FSRS-style scheduler has ever moved this card.

        The question a second scheduler has to ask about a history the first one
        wrote, and the one a surface asks before deciding which numbers are worth
        showing — `ease` is a meaningless constant on a card FSRS moved, and
        `stability` is absent on one SM-2 did.

        Reads one field, because `__post_init__` refuses a card where the two
        disagree. That refusal is what makes a single-field check honest rather
        than a half-answer.
        """
        return self.stability is not None
