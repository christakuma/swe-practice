"""SM-2, in the four-grade variant Anki popularised, as a pure function.

Satisfies `practice.domain.ports.Scheduler`, structurally (ADR 0002). No clock, no
repository, no I/O: a card and a grade in, a new card out. That is what makes the
properties in PLAN.md §9.7 testable by hypothesis over thousands of cards rather
than by three hand-written examples.

**Four grades rather than SM-2's original six.** The published algorithm grades
0 to 5 and asks the solver to distinguish "incorrect, but it felt familiar" from
"incorrect, and the right answer seemed easy to recall once seen". Nobody can do
that honestly about a git exercise they just finished, and a scale people cannot
use produces noise the arithmetic then takes seriously. Four buckets map onto
what a verdict can actually distinguish, which is also what makes
`suggestion.py` possible.

**The interval clamp is the whole reason the property test comes first.** PLAN.md
§9.7 says the monotonicity property only holds if the implementation uses
`max(previous + 1, round(previous * ease))`. At the `ease` floor of 1.3 with a
one-day interval, `round(1 * 1.3) == 1` — a naive multiply leaves the interval
exactly where it was, and "consecutive GOOD strictly increases the interval"
fails on its own stated invariant. The clamp also makes Python's banker's
rounding immaterial here: `round(2.5) == 2` would otherwise stall a two-day
interval at the floor in the same way.

**`AGAIN` resets to one day and never to zero.** A card due *today* is a card the
queue offers again in the same session, which turns a lapse into a loop rather
than a review. One day is the shortest honest answer, and `ReviewCard.is_due`
being `<=` means nothing is lost by it.

**`last_reviewed_at` is set here, which is why the port takes a `datetime`.**
PLAN.md §4.6 wrote the parameter as `today: date`, and a date cannot produce the
timestamp the card carries — so either the scheduler returns a card with a stale
review time for a use case to patch afterwards, or it takes the instant. The
first splits one card's construction across two places and lets `due_on` be
computed from one clock reading while `last_reviewed_at` comes from another;
§9.7's fourth property is precisely that those two agree, and it is stated as a
property *of the scheduler*. So the signature is `now: datetime` and `today` is
derived from it (PLAN.md §16).
"""

from __future__ import annotations

from datetime import timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from practice.domain.review import MINIMUM_EASE, CardState, Grade, ReviewCard

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

__all__ = ["Sm2Scheduler"]

#: What each grade does to the ease factor. SM-2's own numbers, rounded to the
#: two decimal places the published table uses: a lapse costs 0.20, a struggle
#: 0.15, and an easy answer buys 0.15 back. `GOOD` is deliberately 0.0 — it is
#: the grade that means "the schedule was right", so moving the ease on it would
#: make the common case drift.
_EASE_DELTA: Final[Mapping[Grade, float]] = MappingProxyType(
    {
        Grade.AGAIN: -0.20,
        Grade.HARD: -0.15,
        Grade.GOOD: 0.0,
        Grade.EASY: 0.15,
    }
)

#: How much of the ease a non-`GOOD` grade applies. `HARD` ignores the ease
#: outright — a card you struggled with should grow slowly whatever its history
#: says — and `EASY` multiplies on top of it.
_HARD_FACTOR: Final = 1.2
_EASY_BONUS: Final = 1.3

#: The learning steps, in days. A card answered `GOOD` for the first time comes
#: back tomorrow and then in a week; one answered `EASY` skips straight to four
#: days, because "I knew this cold" is a claim the first step exists to test.
_FIRST_INTERVAL: Final = 1
_SECOND_INTERVAL: Final = 6
_EASY_FIRST_INTERVAL: Final = 4

#: What a lapse resets to. See the module docstring for why it is not zero.
_RELEARN_INTERVAL: Final = 1


class Sm2Scheduler:
    """Moves one card. Stateless, so one instance serves the whole process."""

    __slots__ = ()

    def next_card(self, card: ReviewCard, grade: Grade, now: datetime) -> ReviewCard:
        """The card as it stands after being graded at `now`.

        A new card every time rather than a mutation: `ReviewCard` is frozen, and
        the floor on `ease` is re-checked by its `__post_init__` on the way out —
        so a change to the arithmetic here that drove the ease under 1.3 would
        fail at construction rather than be stored.
        """
        ease = max(MINIMUM_EASE, card.ease + _EASE_DELTA[grade])
        lapsed = grade is Grade.AGAIN
        interval = _RELEARN_INTERVAL if lapsed else _interval(card, grade, ease)
        return ReviewCard(
            exercise_id=card.exercise_id,
            due_on=now.date() + timedelta(days=interval),
            state=_state(card, grade),
            ease=ease,
            interval_days=interval,
            # `reps` counts reviews, not successes, which is what makes
            # `reps - lapses` answerable and `reps` itself a usable "how much
            # evidence is behind this card".
            reps=card.reps + 1,
            lapses=card.lapses + 1 if lapsed else card.lapses,
            last_reviewed_at=now,
        )

    def __repr__(self) -> str:
        return "Sm2Scheduler()"


def _interval(card: ReviewCard, grade: Grade, ease: float) -> int:
    """Days until this card is due again, for any grade but `AGAIN`.

    Three cases, and the order they are tested in is the rule: a card with no
    interval yet is on the learning steps, a card still *on* those steps
    graduates, and everything else multiplies.

    The graduation step is gated on `LEARNING` rather than on the interval alone
    so that a lapsed card — reset to one day by the clause above — climbs back at
    two, three, four days instead of being handed the full week it had just
    proved it could not hold.
    """
    previous = card.interval_days
    if previous == 0:
        return _EASY_FIRST_INTERVAL if grade is Grade.EASY else _FIRST_INTERVAL
    if (
        previous == _FIRST_INTERVAL
        and grade is Grade.GOOD
        and card.state is CardState.LEARNING
    ):
        return _SECOND_INTERVAL
    factor = _HARD_FACTOR if grade is Grade.HARD else ease
    if grade is Grade.EASY:
        factor *= _EASY_BONUS
    # The clamp PLAN.md §9.7 names. See the module docstring.
    return max(previous + 1, round(previous * factor))


def _state(card: ReviewCard, grade: Grade) -> CardState:
    """Where the card sits after this review.

    `EASY` graduates immediately, which is the one place the four-grade variant
    departs from treating the steps as mandatory: a card answered easily on first
    sight has shown the step would teach nothing.
    """
    if grade is Grade.AGAIN:
        return CardState.LAPSED
    if card.interval_days == 0 and grade is not Grade.EASY:
        return CardState.LEARNING
    return CardState.REVIEW
