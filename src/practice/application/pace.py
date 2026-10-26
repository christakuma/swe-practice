"""A finish date worked out from how fast the track has really been moving.

This is the answer to "deadlines that are actually useful, and not work". A
deadline somebody has to invent is one they pick arbitrarily and then ignore;
one computed from their own recent history is a statement they can check. So the
track page shows a projection with no setup at all, and a person who wants it as
a commitment pins it with one click (`application/preferences.py`).

**Pace is first passes per day over the last 28 days.** Four weeks, because a
fortnight swings with one busy weekend and a quarter remembers a pace the person
no longer keeps. *First* passes (`Record.first_passed_at`), so redoing a step
adds nothing -- otherwise reviewing old work would shorten the estimate for the
new.

**No projection from thin evidence.** Under three first passes in the window
there is no rate to speak of; a date from one pass would be a guess that looks
like a measurement. So `project` answers `None` and the page says what it is
waiting for rather than inventing a date. A finished track likewise has nothing
left to project.

**A date past a year is reported as "over a year", not printed.** `finish_on` is
`None` then: a date in 2029 is not a plan, and saying "at this pace, more than
a year" is both true and the useful part.

Two tracks that share exercises (`blind-75` sits inside `everything`) count the
same pass in both. That is correct per track -- each is asked how far along *it*
is -- and the per-track pace is not summed anywhere.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

__all__ = [
    "MAX_DAYS",
    "MIN_PASSES",
    "WINDOW_DAYS",
    "GoalReading",
    "Projection",
    "pace_per_day",
    "project",
    "read_goal",
]

WINDOW_DAYS: Final = 28
MIN_PASSES: Final = 3
MAX_DAYS: Final = 365

#: How much faster than the measured pace a goal may ask before it is "behind".
#: A quarter, so a goal that needs 1.2x the recent rate is ambitious and one
#: that needs double is a different plan from the one being lived.
_SLACK: Final = 1.25


@dataclass(frozen=True, slots=True)
class Projection:
    """Where the current pace ends up."""

    per_week: float
    remaining: int
    #: `None` when it is more than `MAX_DAYS` away.
    finish_on: date | None


@dataclass(frozen=True, slots=True)
class GoalReading:
    """A goal date held against what is left and how fast things are moving."""

    days_left: int
    remaining: int
    per_week_needed: float
    is_overdue: bool
    is_behind: bool


def pace_per_day(first_passes: Iterable[date], today: date) -> tuple[float, int]:
    """Rate and the count behind it, over the window ending today."""
    start = today - timedelta(days=WINDOW_DAYS)
    count = sum(1 for day in first_passes if start < day <= today)
    return count / WINDOW_DAYS, count


def project(
    first_passes: Iterable[date], remaining: int, today: date
) -> Projection | None:
    """The date the track finishes at the recent pace, or `None` for no basis."""
    if remaining <= 0:
        return None
    rate, count = pace_per_day(first_passes, today)
    if count < MIN_PASSES:
        return None
    days = math.ceil(remaining / rate)
    return Projection(
        per_week=rate * 7,
        remaining=remaining,
        finish_on=today + timedelta(days=days) if days <= MAX_DAYS else None,
    )


def read_goal(
    target: date, first_passes: Iterable[date], remaining: int, today: date
) -> GoalReading:
    """What the goal asks of the days that are left.

    `days_left` is floored at zero and the needed rate then assumes one day, so
    an overdue goal reports the whole backlog as today's rather than dividing by
    nothing. **Overdue means the day is behind us** (`target < today`): a goal
    that falls *today* still has the day to be met in, and calling it passed
    would offer a re-plan to someone who is about to finish.

    `is_behind` needs a measured pace to compare with; with none, the
    goal cannot be said to be behind, only young.
    """
    days_left = max((target - today).days, 0)
    needed = remaining / max(days_left, 1) * 7
    rate, count = pace_per_day(first_passes, today)
    return GoalReading(
        days_left=days_left,
        remaining=remaining,
        per_week_needed=needed,
        is_overdue=target < today and remaining > 0,
        is_behind=count >= MIN_PASSES and needed > rate * 7 * _SLACK,
    )
