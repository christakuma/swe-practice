"""Attempts in a dict, with database semantics on purpose.

Satisfies `practice.domain.ports.AttemptRepository`. The whole file is five
methods and one decision:

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

    from practice.domain.attempt import Attempt
    from practice.domain.ids import AttemptId, ExerciseId

__all__ = ["InMemoryAttemptRepository"]


class InMemoryAttemptRepository:
    """Every attempt this process has saved, newest last."""

    __slots__ = ("_attempts",)

    def __init__(self) -> None:
        # Insertion-ordered, which is what makes `history_for` return attempts
        # in the order they were started without storing a sort key. A SQLite
        # implementation will have to order explicitly; this one gets it from
        # the dict, and the port's contract is the order, not the mechanism.
        self._attempts: dict[AttemptId, Attempt] = {}

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

    def __len__(self) -> int:
        """How many attempts are stored, for a test that wants to say so."""
        return len(self._attempts)

    def __repr__(self) -> str:
        return f"InMemoryAttemptRepository({len(self._attempts)} attempts)"
