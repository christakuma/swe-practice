"""FSRS-4.5, as a pure function, behind the same `Scheduler` port as SM-2.

Satisfies `practice.domain.ports.Scheduler`, structurally (ADR 0002), and it is
the second implementation PLAN.md §13 asks of every port — the one that decides
whether `Scheduler` was a real seam or a gesture. ADR 0008 predicted the swap
would be *"a second class satisfying the same protocol and one line in
`composition.py`"*; ADR 0018 records what it actually cost.

**Three components instead of one number.** SM-2 carries an ease factor and
multiplies. FSRS models memory as *stability* (how many days until recall
probability falls to 90%), *difficulty* (1 to 10, how fast this item's stability
grows) and *retrievability* (the probability you would recall it right now, which
is a function of the first one and the time elapsed). A review reads
retrievability, moves difficulty by the grade, and grows or resets stability; the
interval is then read off stability.

**At the default 90% retention the interval *is* the stability, exactly.** The
interval formula is `S / F * (R ** (1 / D) - 1)` with `D = -0.5` and
`F = 19/81`, and `0.9 ** -2 - 1 == 0.19 / 0.81 == 19 / 81 == F` — so the two
cancel and the factor is 1 by construction, not by coincidence. That identity is
load-bearing twice over. It is what makes `adopt` below honest: a card SM-2 left
with a seven-day interval can be read as a card with a stability of seven,
rather than reset to new. And it is what lets `interval_days` stay the port's
vocabulary while stability is this scheduler's state.

**The interval clamp is not an SM-2 artefact.** PLAN.md §9.7 names
`max(previous + 1, ...)` as the thing without which "consecutive GOOD strictly
increases the interval" is false at SM-2's ease floor, and reads like a quirk of
SM-2's arithmetic. It is not. Stability grows by a factor of
`1 + k * (exp(w10 * (1 - R)) - 1)`, which is exactly `1` when `R == 1` — and
`R == 1` whenever no days have passed since the last review. Grade a card twice
in one day and FSRS returns a stability it cannot distinguish from the one it was
given, so the same clamp is needed for the same property, from a completely
different direction. The second scheduler found that the clamp belongs to
*whole-day intervals*, not to SM-2 (PLAN.md §16).

**A lapse is clamped against `interval_days`, which SM-2 never had to be.**
FSRS's post-lapse stability is a function of the card's stability, and this card
also carries an `interval_days` that a different scheduler may have written — two
numbers that can disagree, because a stored card is only what the last `save`
wrote. So "a lapse never lengthens an established interval" is enforced against
the number the solver actually saw. SM-2 gets the property for free by resetting
to a constant; this is what it costs when the interval is derived.

**There is no maximum interval**, which FSRS implementations normally have. A
ceiling would break the monotonicity property above the moment a card reached it
— `max(previous + 1, ...)` and `min(ceiling, ...)` cannot both hold — and it
would be protecting against a card nobody will own, since reaching it takes
decades of consecutive `EASY`. `ReviewCard` puts no upper bound on
`interval_days` either, and the port has nowhere to express one, which is a small
honest finding about the port rather than a gap in this file.

**`LEARNING` is SM-2's state and this never writes it.** FSRS has no learning
steps: a card graded `GOOD` on first sight gets `w[2]` days — about four —
rather than one day and then a week. So a card here is `LAPSED` or `REVIEW` and
nothing else, which is the other half of the shared-vocabulary story the two
nullable columns started.
"""

from __future__ import annotations

import math
from datetime import timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from practice.domain.errors import InvalidValueError
from practice.domain.review import (
    MAXIMUM_DIFFICULTY,
    MINIMUM_DIFFICULTY,
    CardState,
    Grade,
    ReviewCard,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

__all__ = ["DEFAULT_WEIGHTS", "FsrsScheduler"]

#: FSRS's own four-point scale, which the four-grade `Grade` enum maps onto
#: exactly. That is not luck: ADR 0008 chose four buckets over SM-2's published
#: six because nobody can honestly distinguish six, and four is what FSRS fits
#: against. The arithmetic below indexes weights by rating, so these numbers are
#: the algorithm's and not an internal convention.
_AGAIN_RATING: Final = 1
_HARD_RATING: Final = 2
_GOOD_RATING: Final = 3
_EASY_RATING: Final = 4

_RATING: Final[Mapping[Grade, int]] = MappingProxyType(
    {
        Grade.AGAIN: _AGAIN_RATING,
        Grade.HARD: _HARD_RATING,
        Grade.GOOD: _GOOD_RATING,
        Grade.EASY: _EASY_RATING,
    }
)

#: FSRS-4.5's published default parameters, in its own order: initial stability
#: per rating (0-3), initial difficulty and its slope (4-5), the difficulty delta
#: and its mean-reversion weight (6-7), the stability growth terms (8-10), the
#: post-lapse terms (11-14), and the hard penalty and easy bonus (15-16).
#:
#: **These are the one thing in this module the test suite cannot check**, and
#: ADR 0008 said so before the module existed: FSRS's advantage comes from
#: parameters fitted to a log of real reviews, and this project has no review log
#: — `sqlite/reviews.py` replaces a card on every review and keeps no history.
#: So there is nothing here to fit them against and nothing to compare them
#: with. They are carried as data under one name, the arithmetic is what the
#: properties hold, and `weights` is injectable precisely so a fitted set could
#: arrive without touching a line of it.
DEFAULT_WEIGHTS: Final[tuple[float, ...]] = (
    0.4872,
    1.4003,
    3.7145,
    13.8206,
    5.1618,
    1.2298,
    0.8975,
    0.0310,
    1.6474,
    0.1367,
    1.0461,
    2.1072,
    0.0793,
    0.3246,
    1.5870,
    0.2272,
    2.8755,
)

#: How many FSRS-4.5 expects. Checked rather than assumed, because the failure of
#: a short list is an `IndexError` twelve lines into the arithmetic.
_WEIGHT_COUNT: Final = 17

#: The forgetting curve's shape. `DECAY` is the exponent and `FACTOR` is fixed by
#: it: `FACTOR == 0.9 ** (1 / DECAY) - 1`, which is what makes an interval at 90%
#: retention equal to the stability. Asserted in the tests rather than left as a
#: comment, because the two constants silently stop agreeing if either is tuned.
_DECAY: Final = -0.5
_FACTOR: Final = 19 / 81

#: The recall probability each interval is aimed at. FSRS's own default, and the
#: one knob a user of this tool might reasonably want; it is not exposed, because
#: an interval computed under one target and stored next to a stability fitted
#: under another is the kind of drift nothing here would catch.
_DESIRED_RETENTION: Final = 0.9

#: `R ** (1 / DECAY) - 1`, the other half of FSRS's interval formula. At the
#: default retention it equals `_FACTOR`, so the two cancel and an interval *is*
#: a stability. Exactly, in arithmetic: `0.9 ** -2 - 1 == 0.19 / 0.81 == 19 / 81`.
#: One ulp out, in float64 -- the test asserts the identity with `isclose` rather
#: than with `==`, which is the honest form of a claim about real numbers
#: evaluated in binary. Computed rather than written out as a number so that
#: tuning the retention target stays a one-line change.
_RETENTION_TERM: Final = float(_DESIRED_RETENTION ** (1 / _DECAY)) - 1

#: A floor on stability, so it stays a usable divisor in the forgetting curve.
#: `ReviewCard` refuses a stored zero for the same reason, one layer out.
_MINIMUM_STABILITY: Final = 0.01

#: Intervals are whole days and a review always moves the card into tomorrow or
#: later, which is the port's one shared behavioural promise.
_MINIMUM_INTERVAL: Final = 1


class FsrsScheduler:
    """Moves one card by FSRS-4.5. Stateless, so one instance serves the process."""

    __slots__ = ("_weights",)

    def __init__(self, weights: Sequence[float] = DEFAULT_WEIGHTS) -> None:
        """`weights` is the seam a fitted parameter set would arrive through.

        Validated on construction rather than on first use: a seventeen-element
        list is the only thing the arithmetic below can read, and a short one
        fails as an `IndexError` in the middle of a stability calculation with
        nothing in the message about where it came from.
        """
        if len(weights) != _WEIGHT_COUNT:
            raise InvalidValueError(
                f"FSRS-4.5 takes {_WEIGHT_COUNT} parameters, got {len(weights)}"
            )
        self._weights = tuple(weights)

    def next_card(self, card: ReviewCard, grade: Grade, now: datetime) -> ReviewCard:
        """The card as it stands after being graded at `now`.

        Both components are computed from the state *before* this review, so the
        order they are written in cannot change the answer. Some FSRS
        implementations feed the freshly-moved difficulty into the stability
        update; doing it from the prior state is a choice, and it is the one that
        makes this function's two halves independent and separately testable.
        """
        rating = _RATING[grade]
        before = self._memory_before(card, rating)
        if before is None:
            stability, difficulty = self._initial_memory(rating)
        else:
            stability, difficulty = self._next_memory(
                before, rating, _elapsed_days(card, now)
            )

        lapsed = grade is Grade.AGAIN
        interval = _interval(stability, previous=card.interval_days, lapsed=lapsed)
        return ReviewCard(
            exercise_id=card.exercise_id,
            due_on=now.date() + timedelta(days=interval),
            state=CardState.LAPSED if lapsed else CardState.REVIEW,
            # Untouched, and left at whatever SM-2 last wrote. FSRS has no use
            # for an ease factor, and zeroing it would destroy the state a switch
            # back to SM-2 would need (`ReviewCard`, and `0002`).
            ease=card.ease,
            interval_days=interval,
            reps=card.reps + 1,
            lapses=card.lapses + 1 if lapsed else card.lapses,
            last_reviewed_at=now,
            stability=stability,
            difficulty=difficulty,
        )

    # --- the three components ---------------------------------------------

    def _memory_before(
        self, card: ReviewCard, rating: int
    ) -> tuple[float, float] | None:
        """The memory state this review starts from, or `None` for a new card.

        Three cases, and the middle one is the interesting half of this module.

        A card FSRS has already moved carries its own state. A card with an
        *interval* but no memory state was scheduled by SM-2, and is **adopted**
        rather than reset: its interval is read as its stability, which the module
        docstring shows is exact at 90% retention, and its difficulty is seeded
        from this grade because that is the only evidence about difficulty there
        is. The alternative — treat it as new — would throw away a month of real
        review history on the day the scheduler was switched, and would do it
        invisibly.

        A card with neither has never been scheduled by anything, and gets
        FSRS's own first-review stability.
        """
        # Both fields rather than `has_memory_state`, which asks the same
        # question: `ReviewCard` refuses a card where one is set and the other is
        # not, so the conjunction cannot be narrower. Written this way because
        # mypy does not narrow a `float | None` through a property.
        stability, difficulty = card.stability, card.difficulty
        if stability is not None and difficulty is not None:
            return stability, difficulty
        if card.interval_days > 0:
            return float(card.interval_days), self._initial_difficulty(rating)
        return None

    def _initial_memory(self, rating: int) -> tuple[float, float]:
        """First sighting: stability straight from the weight for this grade."""
        stability = max(_MINIMUM_STABILITY, self._weights[rating - 1])
        return stability, self._initial_difficulty(rating)

    def _initial_difficulty(self, rating: int) -> float:
        """FSRS-4.5's linear initial difficulty, clamped to the scale."""
        return _clamp(
            self._weights[4] - (rating - _GOOD_RATING) * self._weights[5],
            MINIMUM_DIFFICULTY,
            MAXIMUM_DIFFICULTY,
        )

    def _next_memory(
        self, before: tuple[float, float], rating: int, elapsed: float
    ) -> tuple[float, float]:
        stability, difficulty = before
        retrievability = _retrievability(elapsed, stability)
        moved = (
            self._forget_stability(stability, difficulty, retrievability)
            if rating == _AGAIN_RATING
            else self._recall_stability(stability, difficulty, retrievability, rating)
        )
        return (
            max(_MINIMUM_STABILITY, moved),
            self._next_difficulty(difficulty, rating),
        )

    def _next_difficulty(self, difficulty: float, rating: int) -> float:
        """Move by the grade, then revert a little towards the easy end.

        The mean reversion is FSRS's answer to difficulty ratcheting: without it
        a run of `AGAIN`s pins a card at 10 and nothing can ever bring it back,
        because every subsequent grade moves it by a fixed step from wherever it
        is. `w[7]` is the fraction of the distance travelled back each review.
        """
        moved = difficulty - self._weights[6] * (rating - _GOOD_RATING)
        target = self._initial_difficulty(_EASY_RATING)
        reverted = self._weights[7] * target + (1 - self._weights[7]) * moved
        return _clamp(reverted, MINIMUM_DIFFICULTY, MAXIMUM_DIFFICULTY)

    def _recall_stability(
        self, stability: float, difficulty: float, retrievability: float, rating: int
    ) -> float:
        """Stability after a grade that was not a lapse. Never below the input.

        Every factor in the growth term is non-negative — `11 - difficulty` is at
        least 1 because the scale stops at 10, and `exp(w10 * (1 - R)) - 1` is at
        least 0 because `R` cannot exceed 1 — so the result is `stability` or
        more. It is *exactly* `stability` when `R == 1`, which is the stall the
        interval clamp exists for; see the module docstring.

        The two multipliers are the grades that are not `GOOD`: `HARD` keeps a
        fraction of the growth, `EASY` multiplies it. `GOOD` has neither, because
        it is the grade that means the schedule was right.
        """
        hard_penalty = self._weights[15] if rating == _HARD_RATING else 1.0
        easy_bonus = self._weights[16] if rating == _EASY_RATING else 1.0
        growth = (
            math.exp(self._weights[8])
            * (11 - difficulty)
            * float(stability ** -self._weights[9])
            * (math.exp(self._weights[10] * (1 - retrievability)) - 1)
            * hard_penalty
            * easy_bonus
        )
        return stability * (1 + growth)

    def _forget_stability(
        self, stability: float, difficulty: float, retrievability: float
    ) -> float:
        """Stability after a lapse, and never more than it was.

        The `min` is a decision rather than FSRS-4.5's formula. On a card with a
        very low stability the post-lapse term can come out *above* the input —
        the power on `(S + 1)` is well under 1, so the curve is steep where `S` is
        small — and a scheduler that lengthened the interval because the solver
        had forgotten the answer would be wrong in the way users notice. The
        rejected alternative was to let the model say what it says and weaken the
        property; the property is worth more than fidelity to a formula whose
        parameters this project cannot fit anyway.
        """
        forgotten = (
            self._weights[11]
            * float(difficulty ** -self._weights[12])
            * (float((stability + 1) ** self._weights[13]) - 1)
            * math.exp(self._weights[14] * (1 - retrievability))
        )
        return min(forgotten, stability)

    @property
    def weights(self) -> tuple[float, ...]:
        """The parameters in force, so a caller can report which set it is using."""
        return self._weights

    def __repr__(self) -> str:
        default = " (defaults)" if self._weights == DEFAULT_WEIGHTS else ""
        return f"FsrsScheduler({_WEIGHT_COUNT} parameters{default})"


def _retrievability(elapsed: float, stability: float) -> float:
    """The probability of recall right now, on FSRS's power forgetting curve.

    Bounded in `(0, 1]` for every input this can be handed: `elapsed` is never
    negative and `stability` is always positive, so the base is at least 1 and a
    negative exponent cannot take the result above it. Both bounds are relied on
    by the stability arithmetic, which is why they are stated here.
    """
    return float((1 + _FACTOR * elapsed / stability) ** _DECAY)


def _elapsed_days(card: ReviewCard, now: datetime) -> float:
    """Days since this card was last reviewed, as the forgetting curve wants it.

    Two readings this has to survive, and neither is a hypothetical — a stored
    card is only what the last `save` wrote.

    A card with no `last_reviewed_at` but a real interval is one being adopted
    from SM-2, and the best available reading is *it was reviewed on schedule*:
    an elapsed time equal to the interval puts retrievability at exactly the 90%
    the interval was chosen for, which is the assumption already baked into
    reading its interval as its stability.

    A `last_reviewed_at` in the future of `now` is incoherent, and clamps to zero
    rather than going negative. A negative elapsed time would push
    retrievability above 1 and the growth term below 0, which is the one way the
    arithmetic above could *shrink* stability on a passing grade.
    """
    last = card.last_reviewed_at
    if last is None:
        return float(card.interval_days)
    return max(0.0, float((now.date() - last.date()).days))


def _interval(stability: float, *, previous: int, lapsed: bool) -> int:
    """Days until this card is due again, in whole days.

    `stability / F * (R ** (1 / DECAY) - 1)` is FSRS's interval, and at the
    default retention the second factor is `F` — so the two cancel and the
    interval is the stability. Both are kept rather than cancelled, because the
    cancellation is a property of one retention target and not of the formula.

    Then the two clamps, which are the part that is about this port rather than
    about FSRS, and the module docstring says why each is here.
    """
    days = round(stability / _FACTOR * _RETENTION_TERM)
    if lapsed:
        # `previous or days` so that a card with no interval yet — nothing to be
        # longer than — is bounded by the model rather than by zero.
        return max(_MINIMUM_INTERVAL, min(days, previous or days))
    return max(previous + 1, days)


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))
