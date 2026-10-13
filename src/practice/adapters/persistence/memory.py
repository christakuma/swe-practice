"""Attempts and review cards in dicts, with database semantics on purpose.

Satisfies `practice.domain.ports.AttemptRepository` and
`practice.domain.ports.ReviewRepository`. Two small stores and one decision:

**It stores a deep copy, and hands back a deep copy.** The obvious
implementation keeps the `Attempt` object itself, which makes `save` very nearly
a no-op — the caller already holds the aggregate, so mutating it after saving
"persists" the change by accident. Every test then passes against this store and
the same code loses data against SQLite, where a row is only what the last
`save` wrote. Copying is what makes the fake evidence of anything: a use case
that forgets to save fails here, now, rather than in Phase 6.

`Attempt` is the only mutable thing in the domain, so it is the only type this
applies to; everything it holds is a frozen dataclass or a `str`, which is why
`deepcopy` is cheap enough to do on every call.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

    from practice.domain.attempt import Attempt
    from practice.domain.ids import AttemptId, ExerciseId
    from practice.domain.review import ReviewCard

__all__ = ["InMemoryAttemptRepository", "InMemoryReviewRepository"]


class InMemoryAttemptRepository:
    """Every attempt this process has saved, newest last."""

    __slots__ = ("_attempts", "_current")

    def __init__(self) -> None:
        # Insertion-ordered, which is what makes `history_for` return attempts
        # in the order they were started without storing a sort key. A SQLite
        # implementation will have to order explicitly; this one gets it from
        # the dict, and the port's contract is the order, not the mechanism.
        self._attempts: dict[AttemptId, Attempt] = {}
        self._current: AttemptId | None = None

    def save(self, attempt: Attempt) -> None:
        """Insert or replace. Replacing is the normal case: one attempt is saved
        at least twice, once when it starts and once when it is graded.
        """
        self._attempts[attempt.id] = deepcopy(attempt)

    def get(self, attempt_id: AttemptId) -> Attempt | None:
        """`None` rather than raising for an id nobody saved.

        A caller holding an id that no longer resolves — a stale URL, a
        workspace that outlived its row — is a normal thing to decide about, and
        the use cases turn it into a message.
        """
        attempt = self._attempts.get(attempt_id)
        return deepcopy(attempt) if attempt is not None else None

    def history_for(self, exercise_id: ExerciseId) -> Sequence[Attempt]:
        """Every attempt at one exercise, in the order they were saved."""
        return tuple(
            deepcopy(attempt)
            for attempt in self._attempts.values()
            if attempt.exercise_id == exercise_id
        )

    def active(self) -> Sequence[Attempt]:
        """Every attempt still open, in the order they were saved.

        Answered by filtering, where the SQLite implementation has an index on
        the status. Appropriate for a store that holds one process's attempts and
        another reason the two are both kept: this one is allowed to be the
        simplest thing that satisfies the port, because it is never the one
        holding a year of history.
        """
        return tuple(
            deepcopy(attempt)
            for attempt in self._attempts.values()
            if attempt.is_active
        )

    def completed(self) -> Sequence[Attempt]:
        """Every graded attempt, in the order they were saved.

        By filtering, like `active`, and for the same reason: this store holds
        one process's attempts and is allowed to be the simplest thing that
        satisfies the port. Abandoned attempts are excluded by asking for a
        verdict rather than for a status -- the two cannot disagree, since only
        `complete` sets one, and the verdict is what the summary actually reads.
        """
        return tuple(
            deepcopy(attempt)
            for attempt in self._attempts.values()
            if attempt.verdict is not None
        )

    def mark_current(self, attempt_id: AttemptId) -> None:
        """One slot, overwritten. Not checked against what is stored, because
        the SQLite table is not either (`0004_current_attempt.sql`).
        """
        self._current = attempt_id

    def current(self) -> AttemptId | None:
        return self._current

    def __len__(self) -> int:
        """How many attempts are stored, for a test that wants to say so."""
        return len(self._attempts)

    def __repr__(self) -> str:
        return f"InMemoryAttemptRepository({len(self._attempts)} attempts)"


class InMemoryReviewRepository:
    """Review cards in a dict. No copying, and that asymmetry is the point.

    `ReviewCard` is a frozen dataclass, so there is nothing to alias: a caller
    holding one cannot change it, and the scheduler returns a *new* card rather
    than mutating the old one. The deep copy above exists because `Attempt` is
    mutable and the fake would otherwise hide a missing `save`; here the same
    protection would be ceremony, and writing it anyway would suggest the two
    types carry the same risk.
    """

    __slots__ = ("_cards",)

    def __init__(self) -> None:
        self._cards: dict[ExerciseId, ReviewCard] = {}

    def get_card(self, exercise_id: ExerciseId) -> ReviewCard | None:
        """`None` for an exercise never attempted -- never a card invented here."""
        return self._cards.get(exercise_id)

    def save_card(self, card: ReviewCard) -> None:
        """Insert or replace. One card per exercise; the previous state is gone."""
        self._cards[card.exercise_id] = card

    def due_on(self, day: date) -> Sequence[ReviewCard]:
        """Every card due on or before `day`, longest-overdue first.

        Asks the card rather than comparing the dates itself, so this cannot
        disagree with `ReviewCard.is_due` about what "due" means -- the drift that
        stops a fake being evidence of anything.
        """
        return tuple(
            card
            for card in sorted(
                self._cards.values(), key=lambda card: (card.due_on, card.exercise_id)
            )
            if card.is_due(day)
        )

    def cards(self) -> Sequence[ReviewCard]:
        """Every card, in exercise-id order.

        The order is explicit rather than the dict's, unlike `history_for` above:
        there the port's contract is insertion order and the dict supplies it, and
        here the contract is *by id*, which no insertion order gives.
        """
        return tuple(sorted(self._cards.values(), key=lambda card: card.exercise_id))

    def __len__(self) -> int:
        return len(self._cards)

    def __repr__(self) -> str:
        return f"InMemoryReviewRepository({len(self._cards)} cards)"
