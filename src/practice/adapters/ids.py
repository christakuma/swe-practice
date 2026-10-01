"""The `IdGenerator` port over `uuid4`.

Why this is not a classmethod on `AttemptId`: a `new()` there would put a source
of randomness inside the pure layer, and every test wanting a stable snapshot
would have to patch it. One small adapter instead, and `FakeIdGenerator` hands
out a known sequence (PLAN.md §4.6).
"""

from __future__ import annotations

from uuid import uuid4

from practice.domain.ids import AttemptId

__all__ = ["Uuid4IdGenerator"]


class Uuid4IdGenerator:
    """Satisfies `practice.domain.ports.IdGenerator`.

    `uuid4` rather than a counter or a timestamp, because the first eight hex
    characters name the workspace directory (PLAN.md §8.1) and a sequential id
    would make two concurrent sessions collide on the one thing that has to be
    unique on disk.
    """

    __slots__ = ()

    def new_attempt_id(self) -> AttemptId:
        return AttemptId(uuid4())
