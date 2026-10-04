"""Everything true of *a* scheduler, over every scheduler there is.

The pattern PLAN.md §9 already uses one layer down, where a conformance suite
asserts `GitRepoQuery` and `FakeRepoQuery` agree. A port with one implementation
cannot have a suite like this, which is why Phase 9 had no choice but to write
SM-2's properties as SM-2's own: §9.7 states four, `test_sm2.py` held them, and
whether they were properties of *the port* or of *that algorithm* was an open
question nothing could answer.

**Phase 13 answered it, and the answer is three of four.** The ease floor,
monotonicity under consecutive `GOOD`, and `due_on` always being after the
review are properties of a scheduler. **"`AGAIN` always resets to one day or
less" is SM-2's**, and it stays in `test_sm2.py`: FSRS schedules a lapse from its
own post-lapse stability, which on a long-established card is weeks rather than a
day. What survives as a shared property is the weaker and still useful claim
that **a lapse never lengthens an established interval** -- which SM-2 gets for
free by resetting to a constant, and which FSRS has to be told (ADR 0018).

**The double is deliberately not in here.** `FixedScheduler` pushes every card
out by the same interval whatever the grade, so monotonicity is false of it by
design; it exists so the use-case tests can assert which grade arrived without
depending on arithmetic. A double held to the behavioural contract would be a
third scheduler to maintain. `tests/unit/test_ports.py` is where all three are
held to the *shape*, which is the part a double does have to satisfy.

**The cards are deliberately incoherent**, which `test_sm2.py` argued for first
and which matters more now: a `REVIEW` card with no reps, a `NEW` card with a
500-day interval, and -- new in Phase 13 -- a card carrying FSRS's memory state
that SM-2 is about to move, and a card carrying none that FSRS is about to adopt.
Those last two are not hypothetical. They are what a database looks like after
`PRACTICE_SCHEDULER` is changed, which is a thing a user can do between any two
reviews.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st

from practice.domain import scheduling
from practice.domain.ids import ExerciseId
from practice.domain.review import (
    MAXIMUM_DIFFICULTY,
    MINIMUM_DIFFICULTY,
    MINIMUM_EASE,
    CardState,
    Grade,
    ReviewCard,
)
from practice.domain.scheduling import FsrsScheduler, Sm2Scheduler

if TYPE_CHECKING:
    from practice.domain.ports import Scheduler

TWO_SUM = ExerciseId("katas/two-sum")

#: Bounded so that `due_on` cannot run off the end of the calendar, which is
#: `test_sm2.py`'s reasoning and binds harder here: the monotonicity property
#: reviews twice, and FSRS's growth factor on a long card is larger than SM-2's.
#: A strategy that overflowed would be testing `timedelta`.
instants = st.datetimes(
    min_value=datetime(2020, 1, 1),  # noqa: DTZ001  (hypothesis attaches the zone)
    max_value=datetime(2100, 1, 1),  # noqa: DTZ001
    timezones=st.just(UTC),
)

#: Either both halves of an FSRS memory state or neither, which is the only shape
#: `ReviewCard` will accept -- and both shapes have to be generated, because each
#: is what one scheduler sees after the other has been running.
memory_states = st.one_of(
    st.just((None, None)),
    st.tuples(
        st.floats(min_value=0.01, max_value=3650, allow_nan=False, exclude_min=True),
        st.floats(
            min_value=MINIMUM_DIFFICULTY, max_value=MAXIMUM_DIFFICULTY, allow_nan=False
        ),
    ),
)


@st.composite
def _cards(draw: st.DrawFn) -> ReviewCard:
    stability, difficulty = draw(memory_states)
    return ReviewCard(
        exercise_id=TWO_SUM,
        due_on=draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2100, 1, 1))),
        state=draw(st.sampled_from(CardState)),
        ease=draw(
            st.floats(
                min_value=MINIMUM_EASE,
                max_value=5.0,
                allow_nan=False,
                allow_infinity=False,
            )
        ),
        interval_days=draw(st.integers(min_value=0, max_value=3650)),
        reps=draw(st.integers(min_value=0, max_value=500)),
        lapses=draw(st.integers(min_value=0, max_value=500)),
        last_reviewed_at=draw(st.none() | instants),
        stability=stability,
        difficulty=difficulty,
    )


cards = _cards()
grades = st.sampled_from(Grade)

#: Everything but `AGAIN`, which is the only grade that does not grow the
#: interval by its own arithmetic -- both schedulers shorten it instead.
passing_grades = st.sampled_from([Grade.HARD, Grade.GOOD, Grade.EASY])

#: Every real implementation of the port. A scheduler added later and not added
#: here is a scheduler nothing holds to the contract, which is the one way this
#: file can rot -- `test_every_real_scheduler_is_covered_here` is the guard.
SCHEDULERS: tuple[Scheduler, ...] = (Sm2Scheduler(), FsrsScheduler())


#: Every property below runs once per implementation, named in the test id.
#:
#: `parametrize` and not a fixture, which is not a style choice: hypothesis
#: refuses a function-scoped fixture under `@given`, because a fixture is not
#: reset between generated inputs and that is usually a bug. Here it would not
#: be -- both schedulers are stateless, which is why one instance can serve a
#: whole process -- but the parametrized form says so without having to suppress
#: a health check that is right about every other case.
over_every_scheduler = pytest.mark.parametrize(
    "scheduler", SCHEDULERS, ids=lambda scheduler: type(scheduler).__name__
)


# --- the three of §9.7's four that belong to the port ----------------------


@over_every_scheduler
@given(card=cards, grade=grades, now=instants)
def test_ease_never_drops_below_the_floor(
    scheduler: Scheduler, card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """SM-2's floor, and `ReviewCard` refuses to store a breach of it either.

    A property of the port rather than of SM-2 for a reason worth being precise
    about: FSRS does not *move* the ease, so the claim is that it does not break
    it -- it leaves whatever SM-2 last wrote alone rather than zeroing a field it
    has no use for. That is what makes switching back possible, and a scheduler
    that tidied the field away would fail here.
    """
    assert scheduler.next_card(card, grade, now).ease >= MINIMUM_EASE


@over_every_scheduler
@given(card=cards, now=instants)
def test_consecutive_good_strictly_increases_the_interval(
    scheduler: Scheduler, card: ReviewCard, now: datetime
) -> None:
    """The property the interval clamp exists for, and it exists in both.

    Two reviews, not one, because the case that breaks each implementation is the
    *second*: SM-2 at its ease floor returns `round(1 * 1.3) == 1`, and FSRS with
    no days elapsed returns the stability it was given. Two unrelated causes, one
    fix, and finding that out is what the second implementation was for.
    """
    first = scheduler.next_card(card, Grade.GOOD, now)
    second = scheduler.next_card(first, Grade.GOOD, now + timedelta(days=1))

    assert first.interval_days > card.interval_days
    assert second.interval_days > first.interval_days


@over_every_scheduler
@given(card=cards, grade=grades, now=instants)
def test_a_review_always_moves_the_card_into_the_future(
    scheduler: Scheduler, card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """§9.7's fourth property, and the one that shaped the port's signature.

    It is a statement about two fields of *one* returned card, so the thing that
    sets them has to be one function -- which the `today: date` the plan
    originally sketched made impossible, since nothing could then stamp
    `last_reviewed_at`. Both implementations derive the day from the instant for
    this reason.

    `due_on > now.date()` and not `>=`: `ReviewCard.is_due` is `<=`, so a card
    due today is a card the queue offers again in the same session. That turns a
    review into a loop.
    """
    reviewed = scheduler.next_card(card, grade, now)

    assert reviewed.last_reviewed_at == now
    assert reviewed.due_on > now.date()


# --- what replaces §9.7's fourth, now that it is known to be SM-2's --------


@over_every_scheduler
@given(card=cards, now=instants)
def test_a_lapse_never_lengthens_an_established_interval(
    scheduler: Scheduler, card: ReviewCard, now: datetime
) -> None:
    """The shared half of "`AGAIN` resets to a day or less".

    Guarded on a card that *has* an interval, because a lapse on a card with none
    necessarily lengthens it -- both schedulers return at least a day, and
    anything less would make the card due today and loop. So the claim is about
    an established interval, which is the only kind a solver has ever seen.

    SM-2 satisfies this by resetting to a constant. FSRS has to be told, and
    `fsrs.py` says why: its interval is derived from a stability, while the card
    also carries an `interval_days` that a different scheduler may have written,
    and nothing makes those two numbers agree.
    """
    if card.interval_days < 1:
        return

    reviewed = scheduler.next_card(card, Grade.AGAIN, now)

    assert reviewed.interval_days <= card.interval_days


# --- properties the four imply but do not say ------------------------------


@over_every_scheduler
@given(card=cards, grade=passing_grades, now=instants)
def test_every_grade_but_again_grows_the_interval(
    scheduler: Scheduler, card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """`HARD` included, which is a decision rather than an oversight.

    A `HARD` that shortened the interval would punish honesty: the solver who
    admits a card was a struggle would see it more often than the one who clicks
    `GOOD` out of impatience, and the grade would stop being used. Both
    implementations grow it slowly on `HARD` -- SM-2 by ignoring the ease, FSRS by
    keeping a fraction of the growth term -- and the lapse is what shortens.
    """
    assert scheduler.next_card(card, grade, now).interval_days > card.interval_days


@over_every_scheduler
@given(card=cards, grade=grades, now=instants)
def test_a_review_is_always_counted_and_only_a_lapse_is(
    scheduler: Scheduler, card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """`reps` counts reviews and not successes, which is what makes
    `reps - lapses` answerable and `reps` a usable "how much evidence is behind
    this card". The progress page reads both.
    """
    reviewed = scheduler.next_card(card, grade, now)

    assert reviewed.reps == card.reps + 1
    assert reviewed.lapses == card.lapses + (1 if grade is Grade.AGAIN else 0)


@over_every_scheduler
@given(card=cards, grade=grades, now=instants)
def test_a_lapse_is_the_only_thing_that_lapses_a_card(
    scheduler: Scheduler, card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """The state and the counter cannot disagree, which the progress page relies
    on: it reads `lapses` for the weakest-tags chart and `state` for mastery, and
    a card marked `LAPSED` with no lapse counted would appear in one and not the
    other.
    """
    reviewed = scheduler.next_card(card, grade, now)

    assert (reviewed.state is CardState.LAPSED) == (grade is Grade.AGAIN)


@over_every_scheduler
@given(card=cards, grade=grades, now=instants)
def test_the_card_stays_the_same_card(
    scheduler: Scheduler, card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """Nothing in either algorithm touches identity, and a scheduler that lost it
    would reschedule one exercise onto another's queue entry.
    """
    assert scheduler.next_card(card, grade, now).exercise_id == card.exercise_id


@over_every_scheduler
@given(card=cards, grade=grades, now=instants)
def test_the_card_it_returns_is_one_a_repository_could_store(
    scheduler: Scheduler, card: ReviewCard, grade: Grade, now: datetime
) -> None:
    """Which is already true by construction -- `ReviewCard` is frozen and
    re-validates in `__post_init__`, so a scheduler cannot return an invalid one
    without raising. Stated anyway, because that is the whole reason the bounds
    live on the card rather than inside each scheduler: this test passing is the
    evidence that neither implementation needs to be trusted about them.
    """
    reviewed = scheduler.next_card(card, grade, now)

    # `replace` with nothing replaced, which is the cheapest way to make a frozen
    # dataclass re-run `__post_init__` over its own output.
    assert replace(reviewed) == reviewed


# --- the guard that keeps this file from going stale -----------------------


def test_every_real_scheduler_is_covered_here() -> None:
    """A third implementation added and not parametrized in is a scheduler
    nothing holds to the contract, and no other test would notice.

    Reads the scheduling package's own exports rather than a list written twice.
    `FixedScheduler` is not here to be found, because it lives in the test fakes
    and is deliberately excluded (see the module docstring).
    """
    exported = {
        name
        for name in scheduling.__all__
        if name.endswith("Scheduler")  # the naming convention, not a registry
    }
    covered = {type(scheduler).__name__ for scheduler in SCHEDULERS}

    assert exported == covered
