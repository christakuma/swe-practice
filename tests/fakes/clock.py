"""A clock that only moves when a test moves it."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

DEFAULT_NOW = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)


class FakeClock:
    """Satisfies `practice.domain.ports.Clock`.

    Timezone-aware by construction, because `Attempt` rejects naive timestamps and
    a fake that could hand one over would only ever be used to write a test that
    does not reflect production.
    """

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        if now.tzinfo is None:
            raise ValueError("FakeClock needs an aware datetime")
        self._now = now

    def now(self) -> datetime:
        return self._now

    def today(self) -> date:
        return self._now.date()

    def advance(self, delta: timedelta) -> datetime:
        """Move time forward and return the new reading."""
        if delta < timedelta(0):
            raise ValueError("a clock does not run backwards")
        self._now += delta
        return self._now
