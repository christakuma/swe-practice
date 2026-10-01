"""The `Clock` port over the real clock.

Three lines of implementation and worth having anyway, because it is the other
half of the argument for the port: `FakeClock` in `tests/fakes/clock.py` is the
implementation every test uses, and a port with only a fake is a port that has
not been proven to work (PLAN.md §13).

Timezone-aware by construction. `Attempt` rejects a naive datetime outright, so
a clock that returned one would fail at the first event rather than quietly
recording a timestamp whose meaning depends on where the machine is.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

__all__ = ["SystemClock"]


class SystemClock:
    """Satisfies `practice.domain.ports.Clock`. UTC, always.

    Local time is not offered. An attempt log is a sequence that has to stay
    ordered across a daylight-saving transition, and `today()` deciding which
    cards are due has to mean one thing — the alternative is a review queue that
    changes when you travel.
    """

    __slots__ = ()

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return self.now().date()
