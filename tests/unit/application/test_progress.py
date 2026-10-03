"""`summarise` and `SummariseProgress`: what a history adds up to.

Two halves, and the split is the one `application/graph.py` and
`test_inspect_repository.py` already use. The pure function is driven directly
with attempts built to say one thing each — a streak with a gap in it, a tag that
passes and a tag that does not — and the use case is driven through the real
object graph to prove it gathers the three reads and hands them over unchanged.

Attempts here are built with `Attempt.restore` rather than through the use cases.
Driving `start` and `submit` for twenty attempts spread over a month would mean a
fake clock walked day by day and a test whose subject is buried in its
arrangement; `restore` is the repository's own door and puts a finished attempt on
an exact day in one call, which is the thing every case here varies.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from practice.application.progress import (
    WINDOW_DAYS,
    DayActivity,
    Progress,
    TagMastery,
    summarise,
)
from practice.domain.attempt import Attempt, AttemptPolicy, AttemptStatus
from practice.domain.ids import AttemptId, ExerciseId, tag
from practice.domain.review import CardState, ReviewCard
from tests.fakes import a_kata, a_scenario
from tests.unit.application.helpers import (
    a_failing_verdict,
    a_grade_review,
    a_passing_verdict,
    a_start_attempt,
    a_summarise_progress,
    an_environment,
)
from tests.unit.application.test_review import a_graded_attempt

if TYPE_CHECKING:
    from practice.domain.exercise import Exercise

TODAY = date(2026, 10, 2)
KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

_counter = iter(range(1, 10_000))


def finished(
    exercise: Exercise,
    *,
    day: date = TODAY,
    passed: bool = True,
    minutes: int = 10,
) -> Attempt:
    """A completed attempt that ended on `day`, built through the storage door."""
    started = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC)
    return Attempt.restore(
        attempt_id=AttemptId.parse(f"{next(_counter):08d}-0000-4000-8000-000000000000"),
        exercise_id=exercise.id,
        policy=AttemptPolicy.for_exercise(exercise),
        started_at=started,
        status=AttemptStatus.COMPLETED,
        finished_at=started + timedelta(minutes=minutes),
        verdict=a_passing_verdict() if passed else a_failing_verdict(),
    )


def abandoned(exercise: Exercise, *, day: date = TODAY) -> Attempt:
    """Finished, and never graded. `completed()` excludes these; `summarise`
    skips them too, because the fields it reads are optional on the aggregate.
    """
    started = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC)
    return Attempt.restore(
        attempt_id=AttemptId.parse(f"{next(_counter):08d}-0000-4000-8000-000000000000"),
        exercise_id=exercise.id,
        policy=AttemptPolicy.for_exercise(exercise),
        started_at=started,
        status=AttemptStatus.ABANDONED,
        finished_at=started + timedelta(minutes=1),
    )


def a_card(exercise_id: ExerciseId, *, lapses: int = 0) -> ReviewCard:
    return ReviewCard(
        exercise_id=exercise_id,
        due_on=TODAY,
        state=CardState.REVIEW,
        interval_days=5,
        reps=lapses + 1,
        lapses=lapses,
    )


def a_summary(
    attempts: tuple[Attempt, ...] = (),
    *,
    exercises: tuple[Exercise, ...] = (),
    cards: tuple[ReviewCard, ...] = (),
    today: date = TODAY,
    window_days: int = WINDOW_DAYS,
) -> Progress:
    return summarise(
        attempts=attempts,
        exercises={exercise.id: exercise for exercise in exercises},
        cards=cards,
        today=today,
        window_days=window_days,
    )


# --- the totals ------------------------------------------------------------


class TestTheTotals:
    def test_an_empty_history_answers_zero_rather_than_dividing_by_it(self) -> None:
        progress = a_summary()

        assert progress.total == 0
        assert progress.passed == 0
        assert progress.pass_rate == 0.0
        assert progress.busiest_day == 0
        assert progress.weakest == ()

    def test_it_counts_what_passed(self) -> None:
        kata = a_kata()
        progress = a_summary(
            (finished(kata), finished(kata, passed=False), finished(kata)),
            exercises=(kata,),
        )

        assert progress.total == 3
        assert progress.passed == 2
        assert progress.pass_rate == pytest.approx(2 / 3)

    def test_the_history_is_newest_first(self) -> None:
        """The order a page lists them in, decided here rather than in a
        template: the repository answers oldest-first because that is the order
        an index gives, and reversing it in Jinja would put the decision
        somewhere no test looks.
        """
        kata = a_kata()
        older = finished(kata, day=TODAY - timedelta(days=4))
        newer = finished(kata, day=TODAY)

        progress = a_summary((older, newer), exercises=(kata,))

        assert [attempt.id for attempt in progress.attempts] == [newer.id, older.id]

    def test_an_attempt_with_no_verdict_is_not_a_failure(self) -> None:
        """The guard that is not defensive tidiness. `completed()` promises only
        graded attempts; the fields are still optional on the aggregate, and a
        summary that trusted its caller would count an abandoned attempt as a
        loss.
        """
        kata = a_kata()

        progress = a_summary((finished(kata), abandoned(kata)), exercises=(kata,))

        assert progress.total == 1
        assert progress.passed == 1

    def test_it_reports_how_many_exercises_are_scheduled(self) -> None:
        progress = a_summary(cards=(a_card(KATA), a_card(SCENARIO)))

        assert progress.scheduled == 2


# --- the streak ------------------------------------------------------------


class TestTheStreak:
    def test_practising_today_starts_one(self) -> None:
        kata = a_kata()

        assert a_summary((finished(kata),), exercises=(kata,)).streak_days == 1

    def test_consecutive_days_accumulate(self) -> None:
        kata = a_kata()
        days = tuple(
            finished(kata, day=TODAY - timedelta(days=offset)) for offset in range(4)
        )

        assert a_summary(days, exercises=(kata,)).streak_days == 4

    def test_several_attempts_in_one_day_are_one_day(self) -> None:
        kata = a_kata()
        same_day = (finished(kata), finished(kata), finished(kata))

        assert a_summary(same_day, exercises=(kata,)).streak_days == 1

    def test_yesterday_alone_still_counts(self) -> None:
        """The decision in the module docstring: a streak that reset at midnight
        and came back that evening is a counter nobody would trust.
        """
        kata = a_kata()
        yesterday = finished(kata, day=TODAY - timedelta(days=1))

        assert a_summary((yesterday,), exercises=(kata,)).streak_days == 1

    def test_two_idle_days_is_a_break(self) -> None:
        kata = a_kata()
        before = finished(kata, day=TODAY - timedelta(days=2))

        assert a_summary((before,), exercises=(kata,)).streak_days == 0

    def test_it_counts_only_the_run_ending_now(self) -> None:
        """A fortnight in September does not resurrect this week's zero."""
        kata = a_kata()
        history = (
            finished(kata, day=TODAY - timedelta(days=20)),
            finished(kata, day=TODAY - timedelta(days=19)),
            finished(kata, day=TODAY - timedelta(days=18)),
            finished(kata, day=TODAY),
        )

        assert a_summary(history, exercises=(kata,)).streak_days == 1

    def test_a_failed_attempt_still_counts_as_practice(self) -> None:
        """Turning up is the habit being measured. A streak that only counted
        wins would punish exactly the days worth having.
        """
        kata = a_kata()

        assert (
            a_summary((finished(kata, passed=False),), exercises=(kata,)).streak_days
            == 1
        )


# --- the activity window ---------------------------------------------------


class TestTheWindow:
    def test_it_is_contiguous_and_ends_today(self) -> None:
        """The gaps are the information: seven attempts spread over a month and
        seven consecutive days draw the same chart from a sparse series.
        """
        progress = a_summary(window_days=7)

        assert len(progress.days) == 7
        assert progress.days[0].day == TODAY - timedelta(days=6)
        assert progress.days[-1].day == TODAY
        assert all(day.is_idle for day in progress.days)

    def test_each_day_carries_what_happened_on_it(self) -> None:
        kata = a_kata()
        history = (
            finished(kata, day=TODAY),
            finished(kata, day=TODAY, passed=False),
            finished(kata, day=TODAY - timedelta(days=2)),
        )

        progress = a_summary(history, exercises=(kata,), window_days=3)

        assert [(day.attempts, day.passed) for day in progress.days] == [
            (1, 1),
            (0, 0),
            (2, 1),
        ]
        assert progress.busiest_day == 2

    def test_anything_older_than_the_window_is_not_drawn(self) -> None:
        """It still counts in the totals and could still be in the streak -- the
        window is what the chart shows, not what the history is.
        """
        kata = a_kata()
        ancient = finished(kata, day=TODAY - timedelta(days=90))

        progress = a_summary((ancient,), exercises=(kata,), window_days=7)

        assert progress.total == 1
        assert all(day.is_idle for day in progress.days)


# --- mastery by tag --------------------------------------------------------


class TestMastery:
    def test_one_attempt_counts_against_every_tag_it_carries(self) -> None:
        """Per-tag rates, not a partition: the tags overlap, and splitting an
        attempt three ways would make every rate depend on how many tags the
        author happened to write.
        """
        kata = a_kata(tags=("arrays", "hash-map"))

        progress = a_summary((finished(kata),), exercises=(kata,))

        assert [(row.tag, row.attempted, row.passed) for row in progress.tags] == [
            (tag("arrays"), 1, 1),
            (tag("hash-map"), 1, 1),
        ]

    def test_the_worst_rate_comes_first(self) -> None:
        kata = a_kata(tags=("arrays",))
        scenario = a_scenario()

        progress = a_summary(
            (finished(kata), finished(scenario, passed=False)),
            exercises=(kata, scenario),
        )

        assert [row.tag for row in progress.tags] == [tag("history"), tag("arrays")]
        assert [row.pass_rate for row in progress.tags] == [0.0, 1.0]

    def test_evidence_breaks_a_tie_between_equal_rates(self) -> None:
        """One failure out of one and three out of three are both 0% and are not
        the same problem; the tag with the evidence is the one worth offering.
        """
        thin = a_kata(exercise_id="katas/thin", tags=("thin",))
        thick = a_kata(exercise_id="katas/thick", tags=("thick",))
        history = (
            finished(thin, passed=False),
            *(finished(thick, passed=False) for _ in range(3)),
        )

        progress = a_summary(history, exercises=(thin, thick))

        assert [row.tag for row in progress.tags] == [tag("thick"), tag("thin")]

    def test_lapses_come_from_the_card_and_are_counted_once(self) -> None:
        """A card is per exercise, so practising the same one twice must not
        double a lapse count nothing changed.
        """
        kata = a_kata(tags=("arrays",))

        progress = a_summary(
            (finished(kata), finished(kata)),
            exercises=(kata,),
            cards=(a_card(kata.id, lapses=2),),
        )

        (arrays,) = progress.tags
        assert arrays.attempted == 2
        assert arrays.lapses == 2

    def test_an_attempt_whose_exercise_is_gone_counts_but_carries_no_tags(
        self,
    ) -> None:
        """It happened. Dropping it would let a deleted exercise retroactively
        shorten a streak somebody earned.
        """
        kata = a_kata()

        progress = a_summary((finished(kata),), exercises=())

        assert progress.total == 1
        assert progress.streak_days == 1
        assert progress.tags == ()


class TestWeakness:
    def test_a_tag_that_has_never_gone_wrong_is_not_weak(self) -> None:
        """A dashboard listing a perfect tag under "weakest" teaches you to
        ignore that panel.
        """
        kata = a_kata(tags=("arrays",))

        progress = a_summary((finished(kata),), exercises=(kata,))

        assert progress.tags[0].is_weak is False
        assert progress.weakest == ()

    def test_a_failure_makes_it_weak(self) -> None:
        kata = a_kata(tags=("arrays",))

        progress = a_summary((finished(kata, passed=False),), exercises=(kata,))

        assert [row.tag for row in progress.weakest] == [tag("arrays")]

    def test_a_lapse_makes_it_weak_even_with_a_perfect_rate(self) -> None:
        """The reading pass rate alone misses: the exercise that passes every
        time *after* you have forgotten it twice.
        """
        kata = a_kata(tags=("arrays",))

        progress = a_summary(
            (finished(kata),), exercises=(kata,), cards=(a_card(kata.id, lapses=2),)
        )

        assert progress.tags[0].pass_rate == 1.0
        assert [row.tag for row in progress.weakest] == [tag("arrays")]

    def test_it_offers_a_few_rather_than_all_of_them(self) -> None:
        """A prompt and not a report. The whole table is on `/progress`."""
        exercises = tuple(
            a_kata(exercise_id=f"katas/k{index}", tags=(f"t{index}",))
            for index in range(6)
        )
        history = tuple(finished(exercise, passed=False) for exercise in exercises)

        progress = a_summary(history, exercises=exercises)

        assert len(progress.tags) == 6
        assert len(progress.weakest) == 3


def test_a_tag_nothing_was_attempted_at_reads_as_zero_rather_than_an_error() -> None:
    """Unreachable through `summarise` and reachable by constructing one, which
    is the case worth answering: the consumer is the length of a bar.
    """
    assert TagMastery(tag=tag("arrays"), attempted=0, passed=0, lapses=0).pass_rate == 0


def test_a_day_knows_whether_anything_happened_on_it() -> None:
    assert DayActivity(day=TODAY, attempts=0, passed=0).is_idle is True
    assert DayActivity(day=TODAY, attempts=1, passed=0).is_idle is False


# --- the use case ----------------------------------------------------------


class TestSummariseProgress:
    def test_it_gathers_the_three_reads(self) -> None:
        """Driven through the real use cases, so the attempts it summarises are
        ones the app actually produced -- including the card, which exists only
        because a review was graded.
        """
        world = an_environment()
        a_grade_review(world)(a_graded_attempt(world))

        progress = a_summarise_progress(world)()

        assert progress.total == 1
        assert progress.passed == 1
        assert progress.scheduled == 1
        assert progress.streak_days == 1
        assert [row.tag for row in progress.tags] == [tag("arrays"), tag("hash-map")]

    def test_an_attempt_still_running_is_not_in_it(self) -> None:
        """`completed()` is what it reads, and an open attempt is not finished --
        so a page cannot report one as a loss before it has been graded.
        """
        world = an_environment()
        a_start_attempt(world)(KATA)

        assert a_summarise_progress(world)().total == 0

    def test_the_window_is_a_parameter_and_not_a_constant_read_inside(self) -> None:
        world = an_environment()

        assert len(a_summarise_progress(world)(7).days) == 7
        assert len(a_summarise_progress(world)().days) == WINDOW_DAYS
