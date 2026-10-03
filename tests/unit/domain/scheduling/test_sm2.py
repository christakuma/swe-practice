"""The scheduler, held to the four properties PLAN.md §9.7 states.

**Properties first, examples second, and the order is the point.** §9.7 names the
clamp the monotonicity property requires and says it is *"worth writing the test
first and watching it catch this"* — a naive `round(interval * ease)` leaves a
one-day interval at one day when the ease is at its 1.3 floor, so the
implementation passes every example anyone would think to write and fails its own
stated invariant. The examples below exist for the arithmetic a property cannot
pin down: which of the learning steps a given grade lands on.

The cards hypothesis builds are deliberately allowed to be *incoherent* — a `NEW`
card with a 500-day interval, a `REVIEW` card with no reps. Those states are not
reachable through this scheduler, and that is exactly why they are worth feeding
it: a stored card is only what the last `save` wrote, and a scheduler that assumed
its own output as its input would be making a claim about the whole system that
nothing enforces.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from practice.domain.ids import ExerciseId
from practice.domain.review import (
    MINIMUM_EASE,
    CardState,
    Grade,
    ReviewCard,
)
from practice.domain.scheduling import Sm2Scheduler

TWO_SUM = ExerciseId("katas/two-sum")

NOW = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)
TODAY = NOW.date()

#: Bounded so that `due_on` cannot run off the end of the calendar: the longest
#: interval this can produce from the widest card is a few decades, and `date`
#: stops at 9999. A strategy that overflowed would be testing `timedelta`.
instants = st.datetimes(
    min_value=datetime(2020, 1, 1),  # noqa: DTZ001  (hypothesis attaches the zone)
    max_value=datetime(2100, 1, 1),  # noqa: DTZ001
    timezones=st.just(UTC),
)

cards = st.builds(
    ReviewCard,
    exercise_id=st.just(TWO_SUM),
    due_on=st.dates(min_value=date(2020, 1, 1), max_value=date(2100, 1, 1)),
    state=st.sampled_from(CardState),
    ease=st.floats(
        min_value=MINIMUM_EASE, max_value=5.0, allow_nan=False, allow_infinity=False
    ),
    interval_days=st.integers(min_value=0, max_value=3650),
    reps=st.integers(min_value=0, max_value=500),
    lapses=st.integers(min_value=0, max_value=500),
    last_reviewed_at=st.none() | instants,
)

grades = st.sampled_from(Grade)

#: Everything but `AGAIN`, which is the only grade that does not grow the interval
#: by multiplying — it resets.
passing_grades = st.sampled_from([Grade.HARD, Grade.GOOD, Grade.EASY])


@pytest.fixture
def scheduler() -> Sm2Scheduler:
    return Sm2Scheduler()


#: A card a week into its review phase: the state the multiplying cases start in.
ESTABLISHED = ReviewCard(
    exercise_id=TWO_SUM,
    due_on=TODAY,
    state=CardState.REVIEW,
    ease=2.5,
    interval_days=7,
    reps=3,
    lapses=0,
    last_reviewed_at=NOW - timedelta(days=7),
)


def a_card(**overrides: Any) -> ReviewCard:
    """`ESTABLISHED` with fields replaced, so each test names only what it varies."""
    return replace(ESTABLISHED, **overrides)


# --- the four properties PLAN.md §9.7 names --------------------------------


class TestTheStatedProperties:
    """One test per bullet in §9.7, named after the bullet."""

    @given(card=cards, grade=grades, now=instants)
    def test_ease_never_drops_below_the_floor(
        self, card: ReviewCard, grade: Grade, now: datetime
    ) -> None:
        """SM-2's own floor, and the one `ReviewCard` also refuses to store.

        Belt and braces on purpose (`domain/review.py`): if the arithmetic here
        ever drove the ease under 1.3 the dataclass would raise, so this would
        fail as an error rather than an assertion — which is still a failure, and
        still names the grade that caused it.
        """
        assert Sm2Scheduler().next_card(card, grade, now).ease >= MINIMUM_EASE

    @given(card=cards, now=instants)
    def test_consecutive_good_strictly_increases_the_interval(
        self, card: ReviewCard, now: datetime
    ) -> None:
        """The property the clamp exists for. Two reviews, not one, because the
        case that breaks a naive multiply is the *second* one: the first pushes a
        new card to a day, and `round(1 * 1.3)` is then 1 again.
        """
        scheduler = Sm2Scheduler()

        first = scheduler.next_card(card, Grade.GOOD, now)
        second = scheduler.next_card(first, Grade.GOOD, now + timedelta(days=1))

        assert first.interval_days > card.interval_days
        assert second.interval_days > first.interval_days

    @given(card=cards, now=instants)
    def test_again_always_resets_to_a_day_or_less(
        self, card: ReviewCard, now: datetime
    ) -> None:
        reviewed = Sm2Scheduler().next_card(card, Grade.AGAIN, now)

        assert reviewed.interval_days <= 1
        assert reviewed.due_on <= now.date() + timedelta(days=1)

    @given(card=cards, grade=grades, now=instants)
    def test_due_on_is_always_after_the_review(
        self, card: ReviewCard, grade: Grade, now: datetime
    ) -> None:
        """The property that made the port take a `datetime` rather than a `date`.

        It is a statement about two fields of *one* returned card, so the thing
        that sets them has to be one function — which `today: date` made
        impossible, since nothing could then stamp `last_reviewed_at`.
        """
        reviewed = Sm2Scheduler().next_card(card, grade, now)

        assert reviewed.last_reviewed_at == now
        assert reviewed.due_on > now.date()


# --- properties the four imply but do not say ------------------------------


@given(card=cards, grade=passing_grades, now=instants)
def test_every_grade_but_again_grows_the_interval(
    card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """`HARD` included, which is a decision rather than an oversight.

    A `HARD` that shortened the interval would punish honesty: the solver who
    admits a card was a struggle would see it more often than the one who clicks
    `GOOD` out of impatience, and the grade would stop being used. It grows
    slowly — 1.2x and never the ease — and the lapse is what shortens.
    """
    assert Sm2Scheduler().next_card(card, grade, now).interval_days > card.interval_days


@given(card=cards, grade=grades, now=instants)
def test_a_review_is_always_counted_and_only_a_lapse_is(
    card: ReviewCard, grade: Grade, now: datetime
) -> None:
    reviewed = Sm2Scheduler().next_card(card, grade, now)

    assert reviewed.reps == card.reps + 1
    assert reviewed.lapses == card.lapses + (1 if grade is Grade.AGAIN else 0)


@given(card=cards, grade=grades, now=instants)
def test_the_card_stays_the_same_card(
    card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """Nothing in SM-2 touches identity, and a scheduler that lost it would
    reschedule one exercise onto another's queue entry.
    """
    assert Sm2Scheduler().next_card(card, grade, now).exercise_id == card.exercise_id


# --- the arithmetic a property cannot pin down -----------------------------


class TestTheClampItself:
    """§9.7's worked example, as a test that names it.

    At the ease floor with a one-day interval, `round(1 * 1.3) == 1`: the naive
    implementation returns a card identical in interval to the one it was given,
    the monotonicity property above fails, and this is the case it shrinks to.
    Pinned separately so a regression reads as "the clamp is gone" rather than as
    a hypothesis counter-example someone has to interpret.
    """

    def test_the_floor_case_still_moves(self, scheduler: Sm2Scheduler) -> None:
        card = a_card(ease=MINIMUM_EASE, interval_days=1, state=CardState.REVIEW)

        assert scheduler.next_card(card, Grade.GOOD, NOW).interval_days == 2

    def test_a_short_hard_interval_would_stall_too(
        self, scheduler: Sm2Scheduler
    ) -> None:
        """The same stall from the other direction, and the reason the clamp is
        on the shared return rather than inside the `GOOD` branch.

        `HARD` multiplies by 1.2 whatever the ease, so any interval under two and
        a half days rounds back to itself -- `round(2 * 1.2) == 2`. Python's
        round-half-even would add a third way to stand still; the clamp covers
        all of them without having to enumerate them.
        """
        card = a_card(interval_days=2)

        assert round(2 * 1.2) == 2  # the trap, stated
        assert scheduler.next_card(card, Grade.HARD, NOW).interval_days == 3


class TestTheLearningSteps:
    """What a card does before it is a review card. One-day, then a week."""

    def test_a_new_card_answered_good_comes_back_tomorrow(
        self, scheduler: Sm2Scheduler
    ) -> None:
        card = ReviewCard.new(TWO_SUM, TODAY)

        reviewed = scheduler.next_card(card, Grade.GOOD, NOW)

        assert reviewed.state is CardState.LEARNING
        assert reviewed.interval_days == 1
        assert reviewed.due_on == TODAY + timedelta(days=1)
        assert reviewed.ease == 2.5

    def test_the_second_good_graduates_it_to_a_week(
        self, scheduler: Sm2Scheduler
    ) -> None:
        card = scheduler.next_card(ReviewCard.new(TWO_SUM, TODAY), Grade.GOOD, NOW)

        graduated = scheduler.next_card(card, Grade.GOOD, NOW + timedelta(days=1))

        assert graduated.state is CardState.REVIEW
        assert graduated.interval_days == 6

    def test_easy_on_a_new_card_skips_the_steps(self, scheduler: Sm2Scheduler) -> None:
        """A claim the first step exists to test, and a
        solver who makes it has already passed it.
        """
        reviewed = scheduler.next_card(ReviewCard.new(TWO_SUM, TODAY), Grade.EASY, NOW)

        assert reviewed.state is CardState.REVIEW
        assert reviewed.interval_days == 4
        assert reviewed.ease == pytest.approx(2.65)

    def test_hard_on_a_new_card_stays_on_the_steps(
        self, scheduler: Sm2Scheduler
    ) -> None:
        reviewed = scheduler.next_card(ReviewCard.new(TWO_SUM, TODAY), Grade.HARD, NOW)

        assert reviewed.state is CardState.LEARNING
        assert reviewed.interval_days == 1
        assert reviewed.ease == pytest.approx(2.35)


class TestALapse:
    """What `AGAIN` costs, and what it does not."""

    def test_it_resets_the_interval_and_counts_the_lapse(
        self, scheduler: Sm2Scheduler
    ) -> None:
        reviewed = scheduler.next_card(a_card(interval_days=90), Grade.AGAIN, NOW)

        assert reviewed.state is CardState.LAPSED
        assert reviewed.interval_days == 1
        assert reviewed.lapses == 1
        assert reviewed.ease == pytest.approx(2.3)

    def test_a_lapsed_card_climbs_back_rather_than_graduating(
        self, scheduler: Sm2Scheduler
    ) -> None:
        """The reason the graduation step is gated on `LEARNING` and not on the
        interval alone: a lapsed card is also sitting at one day, and handing it
        the full week is handing back the interval it just failed to hold.
        """
        lapsed = scheduler.next_card(a_card(interval_days=90), Grade.AGAIN, NOW)

        recovering = scheduler.next_card(lapsed, Grade.GOOD, NOW + timedelta(days=1))

        assert recovering.state is CardState.REVIEW
        assert recovering.interval_days == 2

    def test_repeated_lapses_cannot_push_the_ease_under_the_floor(
        self, scheduler: Sm2Scheduler
    ) -> None:
        """Eight lapses from the default ease would reach 0.9 without the floor,
        and `ReviewCard` would refuse to be constructed at all.
        """
        card = a_card()
        for day in range(8):
            card = scheduler.next_card(card, Grade.AGAIN, NOW + timedelta(days=day))

        assert card.ease == MINIMUM_EASE


class TestTheReviewPhase:
    """Multiplying, once the steps are behind it."""

    @pytest.mark.parametrize(
        ("grade", "expected"),
        [
            (Grade.HARD, 12),  # 10 * 1.2
            (Grade.GOOD, 25),  # 10 * 2.5
            (Grade.EASY, 34),  # 10 * 2.65 * 1.3, rounded
        ],
    )
    def test_each_grade_has_its_own_factor(
        self, scheduler: Sm2Scheduler, grade: Grade, expected: int
    ) -> None:
        card = a_card(interval_days=10, ease=2.5)

        assert scheduler.next_card(card, grade, NOW).interval_days == expected

    def test_hard_ignores_the_ease_entirely(self, scheduler: Sm2Scheduler) -> None:
        """A card you struggled with grows slowly whatever its history says,
        which is what keeps a long-established card from jumping a year on the
        review that went badly.
        """
        easy_card = a_card(interval_days=100, ease=4.0)
        hard_card = a_card(interval_days=100, ease=MINIMUM_EASE)

        assert (
            scheduler.next_card(easy_card, Grade.HARD, NOW).interval_days
            == scheduler.next_card(hard_card, Grade.HARD, NOW).interval_days
            == 120
        )


def test_the_scheduler_reads_as_itself_in_a_failure_message() -> None:
    assert repr(Sm2Scheduler()) == "Sm2Scheduler()"
