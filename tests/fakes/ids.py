"""An id generator whose output is readable in a failure message."""

from __future__ import annotations

from uuid import UUID

from practice.domain.ids import AttemptId


class SequentialIdGenerator:
    """Satisfies `practice.domain.ports.IdGenerator`.

    Counts from one, so the ids in a failing assertion are
    `00000000-0000-0000-0000-000000000001` rather than random hex that tells the
    reader nothing about which attempt was which.
    """

    def __init__(self, start: int = 1) -> None:
        self._next = start

    def new_attempt_id(self) -> AttemptId:
        attempt_id = AttemptId(UUID(int=self._next))
        self._next += 1
        return attempt_id
