"""FSRS's own arithmetic, and the three things only it can be held to.

The properties FSRS shares with SM-2 are not here — they are in
`test_scheduler_conformance.py`, parametrized over both schedulers, which is the
point of there being two. What is left is this file's subject: the memory model's
own bounds, the identity that lets an interval be read as a stability, and the
two places where this implementation chose something other than the published
formula.

**The weights are not tested, and cannot be.** ADR 0008 said so before this
module existed: FSRS's advantage comes from parameters fitted to a log of real
reviews, and this project keeps no review log. So there is nothing here to fit
seventeen numbers against. What *is* tested is that the arithmetic around them
holds its stated bounds for every card the system can store — which is the part a
wrong parameter cannot break and a wrong formula can.

One number is pinned to a literal anyway, and it earns it: the first interval for
each grade. 1, 1, 4 and 14 days are what a published FSRS-4.5 implementation
gives on first sight, and they fall straight out of weights 0 to 3 — so they are
the one cheap check that the parameters are in the order this module reads them
in. A transposition anywhere in the first four would show up here as a first
review due in a fortnight.
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from practice.domain.errors import InvalidValueError
from practice.domain.ids import ExerciseId
from practice.domain.review import (
    DEFAULT_EASE,
    MAXIMUM_DIFFICULTY,
    MINIMUM_DIFFICULTY,
    CardState,
    Grade,
    ReviewCard,
)
from practice.domain.scheduling import DEFAULT_WEIGHTS, FsrsScheduler
from practice.domain.scheduling.fsrs import _FACTOR, _RETENTION_TERM

TWO_SUM = ExerciseId("katas/two-sum")

NOW = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
TODAY = NOW.date()


@pytest.fixture
def scheduler() -> FsrsScheduler:
    return FsrsScheduler()


#: A card a fortnight into its review phase, with a memory state of its own.
ESTABLISHED = ReviewCard(
    exercise_id=TWO_SUM,
    due_on=TODAY,
    state=CardState.REVIEW,
    ease=DEFAULT_EASE,
    interval_days=15,
    reps=2,
    lapses=0,
    last_reviewed_at=NOW - timedelta(days=15),
    stability=14.8,
    difficulty=5.12,
)


def a_card(**overrides: Any) -> ReviewCard:
    """`ESTABLISHED` with fields replaced, so each test names only what it varies."""
    return replace(ESTABLISHED, **overrides)


def a_new_card() -> ReviewCard:
    return ReviewCard.new(TWO_SUM, TODAY)


def _difficulty_of(card: ReviewCard) -> float:
    """The difficulty, insisting there is one.

    `ReviewCard.difficulty` is `float | None` because most cards in a real
    database have none, and every card this scheduler returns has one -- so a
    comparison needs the narrowing, and a failed narrowing here is the finding
    rather than a typing nuisance.
    """
    assert card.difficulty is not None
    return card.difficulty


# --- the identity the whole module rests on --------------------------------


def test_an_interval_is_a_stability_at_ninety_percent_retention() -> None:
    """`0.9 ** -2 - 1 == 0.19 / 0.81 == 19 / 81`, which is `_FACTOR`.

    Exact in arithmetic and one ulp out in float64, so it is asserted with
    `isclose`. This is the fact that makes `_memory_before` able to adopt an SM-2
    card by reading its interval as its stability — without it that line would be
    a guess rather than a conversion.
    """
    assert math.isclose(_RETENTION_TERM, _FACTOR)
    assert math.isclose(_RETENTION_TERM, 19 / 81)


@given(stability=st.floats(min_value=0.5, max_value=3650, allow_nan=False))
def test_the_interval_tracks_the_stability_it_was_read_from(stability: float) -> None:
    """The identity again, through the scheduler rather than the constants.

    A card graded `GOOD` comes back with an interval within a day of the
    stability it was given — within, rather than equal to, because the interval is
    whole days and the clamp may add one.
    """
    card = a_card(stability=stability, interval_days=0, last_reviewed_at=None)

    reviewed = FsrsScheduler().next_card(card, Grade.GOOD, NOW)

    assert reviewed.stability is not None
    assert abs(reviewed.interval_days - reviewed.stability) <= 1


# --- the memory model's own bounds -----------------------------------------

cards = st.builds(
    ReviewCard,
    exercise_id=st.just(TWO_SUM),
    due_on=st.dates(min_value=date(2020, 1, 1), max_value=date(2100, 1, 1)),
    state=st.sampled_from(CardState),
    interval_days=st.integers(min_value=0, max_value=3650),
    reps=st.integers(min_value=0, max_value=500),
    lapses=st.integers(min_value=0, max_value=500),
    last_reviewed_at=st.none()
    | st.datetimes(
        min_value=datetime(2020, 1, 1),  # noqa: DTZ001  (hypothesis attaches the zone)
        max_value=datetime(2100, 1, 1),  # noqa: DTZ001
        timezones=st.just(UTC),
    ),
    stability=st.floats(
        min_value=0.01, max_value=3650, allow_nan=False, exclude_min=True
    ),
    difficulty=st.floats(
        min_value=MINIMUM_DIFFICULTY, max_value=MAXIMUM_DIFFICULTY, allow_nan=False
    ),
)

grades = st.sampled_from(Grade)


@given(card=cards, grade=grades)
def test_difficulty_stays_on_the_scale(card: ReviewCard, grade: Grade) -> None:
    """Held over incoherent cards for the reason `test_sm2.py` states: a stored
    card is only what the last `save` wrote, and `11 - difficulty` going negative
    would silently invert the growth term rather than fail.
    """
    reviewed = FsrsScheduler().next_card(card, grade, NOW)

    assert reviewed.difficulty is not None
    assert MINIMUM_DIFFICULTY <= reviewed.difficulty <= MAXIMUM_DIFFICULTY


@given(card=cards, grade=grades)
def test_stability_stays_positive(card: ReviewCard, grade: Grade) -> None:
    """Which `ReviewCard` also refuses, so a breach here fails at construction.

    Belt and braces for the same reason as SM-2's ease floor, and the stake is
    higher: stability is a divisor in the forgetting curve, so a zero is a
    `ZeroDivisionError` on the *next* review rather than a wrong interval on this
    one.
    """
    reviewed = FsrsScheduler().next_card(card, grade, NOW)

    assert reviewed.stability is not None
    assert reviewed.stability > 0


@given(card=cards, grade=grades)
def test_every_review_leaves_a_memory_state(card: ReviewCard, grade: Grade) -> None:
    """Including the first. A card this scheduler has moved can always be moved
    by it again without being adopted a second time, which is what stops the
    adoption path from re-seeding a stability it has already computed.
    """
    assert FsrsScheduler().next_card(card, grade, NOW).has_memory_state is True


@given(elapsed=st.integers(min_value=0, max_value=3650))
def test_the_longer_it_has_been_the_further_the_interval_moves(elapsed: int) -> None:
    """Retrievability falls as time passes, and the growth term rises with it.

    The memory model's one externally visible claim: reviewing a card late earns
    *more* stability than reviewing it early, because recalling something you were
    about to forget is better evidence than recalling something you saw
    yesterday. It is also the mechanism behind the stall — at `elapsed == 0`
    there is no evidence at all and the growth term is zero.
    """
    scheduler = FsrsScheduler()
    card = a_card(last_reviewed_at=NOW - timedelta(days=elapsed))
    baseline = scheduler.next_card(
        a_card(last_reviewed_at=NOW), Grade.GOOD, NOW
    ).stability

    late = scheduler.next_card(card, Grade.GOOD, NOW).stability

    assert late is not None
    assert baseline is not None
    assert late >= baseline


# --- the first review, which is where the parameters show -------------------


@pytest.mark.parametrize(
    ("grade", "interval"),
    [(Grade.AGAIN, 1), (Grade.HARD, 1), (Grade.GOOD, 4), (Grade.EASY, 14)],
)
def test_a_new_card_gets_fsrs_first_intervals(
    scheduler: FsrsScheduler, grade: Grade, interval: int
) -> None:
    """Weights 0 to 3, rounded. See the module docstring for why this is pinned.

    Note what is *not* here: SM-2's one-day-then-a-week learning steps. FSRS has
    no learning phase, so a card answered `GOOD` on first sight goes straight to
    four days — and the `LEARNING` state is never written.
    """
    reviewed = scheduler.next_card(a_new_card(), grade, NOW)

    assert reviewed.interval_days == interval
    # `LAPSED` or `REVIEW` and never `LEARNING`, which mypy can prove from this
    # one line -- it rejects `is not CardState.LEARNING` below it as a
    # non-overlapping comparison. Worth recording rather than asserting twice.
    assert reviewed.state is (
        CardState.LAPSED if grade is Grade.AGAIN else CardState.REVIEW
    )


@pytest.mark.parametrize(
    ("grade", "difficulty"),
    [
        (Grade.AGAIN, 7.62),
        (Grade.HARD, 6.39),
        (Grade.GOOD, 5.16),
        (Grade.EASY, 3.93),
    ],
)
def test_a_new_cards_difficulty_is_read_off_the_grade(
    scheduler: FsrsScheduler, grade: Grade, difficulty: float
) -> None:
    """The linear initial difficulty: `w4 - (rating - 3) * w5`, one step per grade.

    Pinned alongside the intervals above and for the same reason — weights 4 and
    5 transposed would still produce four plausible-looking numbers, in the wrong
    order.
    """
    reviewed = scheduler.next_card(a_new_card(), grade, NOW)

    assert reviewed.difficulty == pytest.approx(difficulty, abs=0.01)


def test_the_four_difficulties_are_ordered_hardest_first(
    scheduler: FsrsScheduler,
) -> None:
    """The ordering is the claim; the numbers above are how it is spelled."""
    difficulties = [
        _difficulty_of(scheduler.next_card(a_new_card(), grade, NOW)) for grade in Grade
    ]

    assert difficulties == sorted(difficulties, reverse=True)


# --- adoption: the half of this module that is about the other scheduler ----


class TestAdoptingAnSm2Card:
    """A card with an interval and no memory state, which is every card in a
    database SM-2 filled (`0002_fsrs_memory_state.sql`).
    """

    def test_its_interval_is_read_as_its_stability(
        self, scheduler: FsrsScheduler
    ) -> None:
        """Not reset to new, which is the alternative and would be invisible.

        A card SM-2 had pushed out to a fortnight comes back further out, not
        back at four days: the history is adopted. The test asserts the gap
        rather than a number, because the number is the memory model's and the
        claim is about which of two starting points was used.
        """
        sm2_card = ReviewCard(
            exercise_id=TWO_SUM,
            due_on=TODAY,
            state=CardState.REVIEW,
            ease=2.5,
            interval_days=15,
            reps=3,
            lapses=0,
            last_reviewed_at=NOW - timedelta(days=15),
        )

        adopted = scheduler.next_card(sm2_card, Grade.GOOD, NOW)
        from_scratch = scheduler.next_card(a_new_card(), Grade.GOOD, NOW)

        assert adopted.interval_days > sm2_card.interval_days
        assert adopted.interval_days > from_scratch.interval_days
        assert adopted.has_memory_state is True

    def test_a_card_with_no_interval_is_not_adopted_but_started(
        self, scheduler: FsrsScheduler
    ) -> None:
        """There is nothing to adopt: an interval of zero is a card SM-2 created
        and never reviewed, and reading it as a stability of zero would be a
        division by it.
        """
        never_reviewed = a_card(
            interval_days=0, stability=None, difficulty=None, last_reviewed_at=None
        )

        assert scheduler.next_card(never_reviewed, Grade.GOOD, NOW).interval_days == 4

    def test_an_adopted_card_with_no_review_time_is_assumed_on_schedule(
        self, scheduler: FsrsScheduler
    ) -> None:
        """`last_reviewed_at` is nullable, and an adopted card may have none.

        Reading the elapsed time as the interval puts retrievability at exactly
        the 90% the interval was chosen for, which is the same assumption already
        made by reading the interval as the stability. The alternative — zero
        elapsed — would stall the growth term and hand the card back one day
        longer than it was, which is the clamp standing in for a scheduler.
        """
        no_timestamp = a_card(
            interval_days=15, stability=None, difficulty=None, last_reviewed_at=None
        )

        reviewed = scheduler.next_card(no_timestamp, Grade.GOOD, NOW)

        assert reviewed.interval_days > 16

    def test_a_card_fsrs_already_moved_is_not_adopted_again(
        self, scheduler: FsrsScheduler
    ) -> None:
        """Its own stability wins over its interval, and the two can disagree —
        a switch back to SM-2 and forward again leaves exactly that card.
        """
        disagreeing = a_card(stability=3.0, interval_days=400)

        reviewed = scheduler.next_card(disagreeing, Grade.GOOD, NOW)

        assert reviewed.stability is not None
        assert reviewed.stability < 400


def test_switching_schedulers_leaves_sm2s_ease_untouched(
    scheduler: FsrsScheduler,
) -> None:
    """FSRS has no use for an ease factor and does not clear it.

    Which is what makes the switch reversible: zeroing `ease` would leave SM-2
    nothing to multiply if the choice were changed back, and the floor of 1.3
    means `ReviewCard` could not even store a zero.
    """
    assert scheduler.next_card(a_card(ease=1.75), Grade.GOOD, NOW).ease == 1.75


# --- the two places this implementation departs from the formula ------------


class TestTheStallTheClampExistsFor:
    """PLAN.md §9.7's clamp, arrived at from the other direction.

    §9.7 names `max(previous + 1, ...)` as the fix for SM-2 stalling at its ease
    floor, which reads like a quirk of one algorithm's arithmetic. It is not: FSRS
    stalls too, for an unrelated reason, and needs the same clamp. Pinned here so
    that a regression reads as "the clamp is gone" rather than as a conformance
    counter-example someone has to interpret.
    """

    def test_a_same_day_review_cannot_move_the_stability(
        self, scheduler: FsrsScheduler
    ) -> None:
        """`R == 1` when no days have passed, and the growth term is
        `exp(w10 * (1 - R)) - 1`, which is then exactly zero. The stated trap.
        """
        card = a_card(last_reviewed_at=NOW)

        reviewed = scheduler.next_card(card, Grade.GOOD, NOW)

        assert reviewed.stability == card.stability

    def test_the_interval_still_moves(self, scheduler: FsrsScheduler) -> None:
        card = a_card(interval_days=15, last_reviewed_at=NOW)

        assert scheduler.next_card(card, Grade.GOOD, NOW).interval_days == 16

    def test_a_review_time_in_the_future_is_clamped_to_no_time_at_all(
        self, scheduler: FsrsScheduler
    ) -> None:
        """An incoherent card, and the one way the growth term could go negative:
        a negative elapsed time puts retrievability above 1, and `exp(w10 * (1 -
        R)) - 1` below zero, which would *shrink* stability on a passing grade.
        """
        card = a_card(last_reviewed_at=NOW + timedelta(days=30))

        reviewed = scheduler.next_card(card, Grade.GOOD, NOW)

        assert reviewed.stability == card.stability


class TestALapseNeverLengthensTheInterval:
    """The `min` in `_forget_stability`, which is not FSRS-4.5's formula.

    The published post-lapse term can come out above the input stability when the
    input is small — the power on `(S + 1)` is well under 1, so the curve is steep
    down there. A scheduler that lengthened the interval because the solver had
    forgotten the answer is wrong in the way users notice, so the model is
    clamped. The conformance suite holds both schedulers to the property; these
    are the cases that show where it bites.
    """

    def test_a_lapse_on_a_low_stability_card_does_not_grow_it(
        self, scheduler: FsrsScheduler
    ) -> None:
        card = a_card(stability=0.5, interval_days=1)

        reviewed = scheduler.next_card(card, Grade.AGAIN, NOW)

        assert reviewed.stability is not None
        assert reviewed.stability <= 0.5
        assert reviewed.interval_days == 1

    def test_a_lapse_is_bounded_by_the_interval_the_solver_saw(
        self, scheduler: FsrsScheduler
    ) -> None:
        """The second clamp, and the one SM-2 never needed.

        This card's stability and its `interval_days` disagree, which a stored
        card is allowed to do — it is only what the last `save` wrote, and the
        last save may have been a different scheduler. The post-lapse interval is
        held to the smaller of the two, because the number the solver actually saw
        is the one they would notice getting longer.
        """
        disagreeing = a_card(stability=3650, interval_days=5)

        assert scheduler.next_card(disagreeing, Grade.AGAIN, NOW).interval_days <= 5

    def test_a_lapse_on_a_card_with_no_interval_is_bounded_by_the_model(
        self, scheduler: FsrsScheduler
    ) -> None:
        """`previous or days`: there is nothing to be shorter than, so the model
        decides. A naive `min(days, previous)` would floor every first lapse at a
        day whatever the memory state said.
        """
        fresh = a_card(interval_days=0, stability=200.0, last_reviewed_at=None)

        assert scheduler.next_card(fresh, Grade.AGAIN, NOW).interval_days > 1


class TestTheGradesThatAreNotGood:
    """`HARD` keeps a fraction of the growth, `EASY` multiplies it, `GOOD` has
    neither — because it is the grade that means the schedule was right.
    """

    def test_hard_grows_the_least_and_easy_the_most(
        self, scheduler: FsrsScheduler
    ) -> None:
        intervals = [
            scheduler.next_card(a_card(), grade, NOW).interval_days
            for grade in (Grade.HARD, Grade.GOOD, Grade.EASY)
        ]

        assert intervals == sorted(intervals)
        assert len(set(intervals)) == 3

    def test_a_lapse_moves_difficulty_up_and_an_easy_moves_it_down(
        self, scheduler: FsrsScheduler
    ) -> None:
        card = a_card()

        assert card.difficulty is not None
        harder = scheduler.next_card(card, Grade.AGAIN, NOW).difficulty
        easier = scheduler.next_card(card, Grade.EASY, NOW).difficulty
        assert harder is not None
        assert easier is not None
        assert harder > card.difficulty > easier

    def test_difficulty_reverts_towards_the_easy_end_rather_than_ratcheting(
        self, scheduler: FsrsScheduler
    ) -> None:
        """`w[7]`'s whole job, and `GOOD` is the grade that shows it.

        `GOOD`'s delta is exactly zero — it is the grade that means the schedule
        was right — so under a pure delta model a card pinned at 10 by a run of
        lapses would answer `GOOD` forever and stay at 10. The mean reversion is
        what pulls it back, and this is the only grade where the pull is the whole
        of the movement.
        """
        pinned = a_card(difficulty=MAXIMUM_DIFFICULTY)

        recovering = scheduler.next_card(pinned, Grade.GOOD, NOW)

        assert recovering.difficulty is not None
        assert recovering.difficulty < MAXIMUM_DIFFICULTY

    def test_a_lapse_at_the_top_of_the_scale_stays_there(
        self, scheduler: FsrsScheduler
    ) -> None:
        """The reversion is a fraction of the distance, not an override: it does
        not rescue a card from a grade that would push it past the ceiling.
        """
        pinned = a_card(difficulty=MAXIMUM_DIFFICULTY)

        assert (
            scheduler.next_card(pinned, Grade.AGAIN, NOW).difficulty
            == MAXIMUM_DIFFICULTY
        )

    def test_difficulty_cannot_be_driven_below_the_scale(
        self, scheduler: FsrsScheduler
    ) -> None:
        card = a_card(difficulty=MINIMUM_DIFFICULTY)

        reviewed = scheduler.next_card(card, Grade.EASY, NOW)

        assert _difficulty_of(reviewed) >= MINIMUM_DIFFICULTY


# --- the parameters as data -------------------------------------------------


def test_the_parameters_are_injectable_and_reported() -> None:
    """The seam ADR 0008 names: fitted parameters arrive without touching a line
    of arithmetic. `weights` is on the class so a caller can say which set it is
    running, which is the only honest thing to say about numbers this project
    cannot validate.
    """
    tuned = tuple(weight * 1.1 for weight in DEFAULT_WEIGHTS)

    assert FsrsScheduler(tuned).weights == tuned
    assert FsrsScheduler().weights == DEFAULT_WEIGHTS


def test_tuned_parameters_change_the_schedule(scheduler: FsrsScheduler) -> None:
    """Otherwise `weights` would be a decorative constructor argument."""
    impatient = list(DEFAULT_WEIGHTS)
    impatient[8] = DEFAULT_WEIGHTS[8] + 1.0  # the stability growth factor

    assert (
        FsrsScheduler(impatient).next_card(a_card(), Grade.GOOD, NOW).interval_days
        > scheduler.next_card(a_card(), Grade.GOOD, NOW).interval_days
    )


@pytest.mark.parametrize("count", [0, 16, 18])
def test_the_wrong_number_of_parameters_is_refused_on_construction(
    count: int,
) -> None:
    """Rather than as an `IndexError` twelve lines into a stability calculation
    with nothing in the message about where the list came from.
    """
    with pytest.raises(InvalidValueError, match="takes 17 parameters"):
        FsrsScheduler([1.0] * count)


def test_it_describes_itself_and_says_whether_the_parameters_are_the_defaults() -> None:
    """The one thing a repr can usefully say here: which numbers are in force."""
    assert "defaults" in repr(FsrsScheduler())
    assert "defaults" not in repr(FsrsScheduler([1.0] * 17))
