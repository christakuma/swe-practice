"""What the person has chosen about the tool, read and written over one port.

**Plain functions over `SettingsRepository`, not a use case each.** Every one of
these is a single read or write with a default and a parse; a class per setting
would be the "abstraction that forwards one call unchanged" CLAUDE.md warns
about. They live in `application/` rather than in the store because the *meaning*
of a key -- that `"0"` is off, that a goal is an ISO date -- is policy, and the
store is deliberately policy-free.

**Review scheduling is a preference, defaulting to on.** The spaced-repetition
machinery (cards, the due queue, the Schedule panel) is unchanged and nothing is
deleted by turning it off: the cards stay where they are, and turning it back on
resumes the schedule rather than restarting it. Off only means the product stops
*asking* -- no queue on the dashboard, no grade to press after an attempt.

**A goal is the person's own date, one key per track.** What makes it useful
without being work is `application/pace.py`, which proposes the date from how
fast the track has actually been moving; this module only remembers the answer.
An unreadable stored value is treated as no goal rather than raised about: a
hand-edited database should lose a deadline, not the track page.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from practice.domain.ports import SettingsRepository

__all__ = [
    "clear_goal",
    "goal_for",
    "reviews_enabled",
    "set_goal",
    "set_reviews_enabled",
]

_REVIEWS: Final = "reviews_enabled"
_GOAL_PREFIX: Final = "goal:"


def reviews_enabled(settings: SettingsRepository) -> bool:
    """On unless the person turned it off. Absent means on."""
    return settings.get(_REVIEWS) != "0"


def set_reviews_enabled(settings: SettingsRepository, *, enabled: bool) -> None:
    settings.set(_REVIEWS, "1" if enabled else "0")


def goal_for(settings: SettingsRepository, track: str) -> date | None:
    """The finish-by date set for a track, or `None`."""
    stored = settings.get(_GOAL_PREFIX + track)
    if stored is None:
        return None
    try:
        return date.fromisoformat(stored)
    except ValueError:
        return None


def set_goal(settings: SettingsRepository, track: str, target: date) -> None:
    settings.set(_GOAL_PREFIX + track, target.isoformat())


def clear_goal(settings: SettingsRepository, track: str) -> None:
    settings.delete(_GOAL_PREFIX + track)
