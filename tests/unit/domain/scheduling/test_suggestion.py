"""The grade the tool proposes, read off a finished attempt.

Three inputs — the verdict, the hints revealed, the time against the author's
estimate — and one ceiling. The tests are grouped by which of those a case is
about, and the last group is the ceiling itself, which is the only part of the
rule that is a judgement rather than arithmetic.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from practice.domain.attempt import Attempt, AttemptMode, AttemptPolicy
from practice.domain.errors import AttemptStateError
from practice.domain.ids import AttemptId
from practice.domain.review import Grade
from practice.domain.scheduling import suggest_grade
from practice.domain.verdict import CheckReport, Severity, Verdict
from tests.fakes import FakeClock, a_kata

if TYPE_CHECKING:
    from practice.domain.exercise import Exercise

STARTED = FakeClock().now()


def an_attempt(
    exercise: Exercise, *, mode: AttemptMode = AttemptMode.PRACTICE
) -> Attempt:
    return Attempt(
        attempt_id=AttemptId.parse("00000001-0000-4000-8000-000000000000"),
        exercise_id=exercise.id,
        policy=AttemptPolicy.for_exercise(exercise, mode=mode),
        started_at=STARTED,
    )


def a_verdict(*, passed: bool = True, advisory: bool = False) -> Verdict:
    """One required check, and optionally one failing advisory beside it."""
    reports = [
        CheckReport(
            check_id="finds-the-pair",
            label="Finds the two positions that add up to the target.",
            severity=Severity.REQUIRED,
            passed=passed,
        )
    ]
    if advisory:
        reports.append(
            CheckReport(
                check_id="one-pass",
                label="Scans the list once.",
                severity=Severity.ADVISORY,
                passed=False,
                explanation="Two passes is the same answer at twice the cost.",
            )
        )
    return Verdict(reports=tuple(reports))


def a_finished_attempt(
    *,
    passed: bool = True,
    advisory: bool = False,
    hints: int = 0,
    minutes: int = 1,
    estimated_minutes: int = 20,
    mode: AttemptMode = AttemptMode.PRACTICE,
) -> tuple[Attempt, Exercise]:
    """An attempt that has run `minutes` and been graded, with `hints` revealed.

    Built through the aggregate rather than `restore`, so the hint events are
    real log entries and `hints_revealed` is counting the same thing the live
    attempt would count.
    """
    exercise = a_kata(
        estimated_minutes=estimated_minutes,
        hints=("Trade space for time.", "A dict of what you have seen.", "One pass."),
    )
    attempt = an_attempt(exercise, mode=mode)
    for index in range(hints):
        attempt.reveal_next_hint(at=STARTED + timedelta(seconds=index))
    attempt.complete(
        a_verdict(passed=passed, advisory=advisory),
        at=STARTED + timedelta(minutes=minutes),
    )
    return attempt, exercise


class TestTheThreeInputs:
    """One penalty each, and what each of them reads."""

    def test_a_clean_pass_is_easy(self) -> None:
        attempt, exercise = a_finished_attempt()

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.grade is Grade.EASY
        assert suggestion.is_clean is True
        assert suggestion.penalties == 0

    def test_a_failure_is_again_whatever_else_happened(self) -> None:
        """Short-circuit, not a penalty: a solver who did not get there did not
        get there, and no amount of speed changes it.
        """
        attempt, exercise = a_finished_attempt(passed=False, hints=0, minutes=1)

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.grade is Grade.AGAIN
        assert suggestion.passed is False

    def test_an_advisory_costs_a_step(self) -> None:
        """§4.4's whole bet, in the scheduler: *correct tree, but you rewrote
        history that was already published* is a pass that should come back
        sooner than a clean one.
        """
        attempt, exercise = a_finished_attempt(advisory=True)

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.grade is Grade.GOOD
        assert suggestion.advisories == 1

    def test_a_revealed_hint_costs_a_step(self) -> None:
        attempt, exercise = a_finished_attempt(hints=1)

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.grade is Grade.GOOD
        assert suggestion.hints_used == 1

    def test_more_hints_cost_no_more_than_one_step(self) -> None:
        """The reading is *any* hint, not how many. Two hints on an exercise with
        two is not twice as bad as one on an exercise with ten, and weighting
        them would make the suggestion depend on how generously the author wrote.
        """
        one, exercise = a_finished_attempt(hints=1)
        both, _ = a_finished_attempt(hints=2)

        assert suggest_grade(one, exercise).grade is Grade.GOOD
        assert suggest_grade(both, exercise).grade is Grade.GOOD

    def test_overrunning_the_estimate_costs_a_step(self) -> None:
        attempt, exercise = a_finished_attempt(minutes=25, estimated_minutes=20)

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.grade is Grade.GOOD
        assert suggestion.overran is True

    def test_finishing_inside_the_estimate_costs_nothing(self) -> None:
        attempt, exercise = a_finished_attempt(minutes=20, estimated_minutes=20)

        assert suggest_grade(attempt, exercise).overran is False

    def test_being_fast_earns_nothing_extra(self) -> None:
        """There is no grade above `EASY`, deliberately: the fast paths through
        these exercises are often the ones the advisories exist to flag.
        """
        quick, exercise = a_finished_attempt(minutes=1, estimated_minutes=60)

        assert suggest_grade(quick, exercise).grade is Grade.EASY


class TestTheCeiling:
    """A pass never suggests `AGAIN`, however badly it went."""

    def test_two_penalties_reach_hard(self) -> None:
        attempt, exercise = a_finished_attempt(advisory=True, hints=2)

        assert suggest_grade(attempt, exercise).grade is Grade.HARD

    def test_all_three_stop_at_hard(self) -> None:
        """`AGAIN` means *you did not know this*, and someone whose end state
        satisfied every required check did know it. Collapsing a messy pass into
        the lapse bucket would schedule it as though nothing had been learned.
        """
        attempt, exercise = a_finished_attempt(
            advisory=True, hints=3, minutes=90, estimated_minutes=20
        )

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.penalties == 3
        assert suggestion.grade is Grade.HARD
        assert suggestion.is_clean is False


class TestWhatItRefuses:
    def test_an_attempt_that_has_not_finished(self) -> None:
        """Elapsed time only means something once it has stopped running, and a
        suggestion that changed on every page refresh would be worse than none.
        """
        exercise = a_kata()

        with pytest.raises(AttemptStateError, match="no verdict"):
            suggest_grade(an_attempt(exercise), exercise)

    def test_an_abandoned_attempt(self) -> None:
        """Finished, and still ungradable: `abandon` sets `finished_at` and
        leaves the verdict `None`, so the check has to be on both.
        """
        exercise = a_kata()
        attempt = an_attempt(exercise)
        attempt.abandon(at=STARTED + timedelta(minutes=1))

        with pytest.raises(AttemptStateError, match="abandoned"):
            suggest_grade(attempt, exercise)


class TestAnInterviewIsReadByTheSameRule:
    """What Phase 15 did and did not have to change here.

    The rule is untouched: an interview's deadline *is* `estimated_minutes`, so
    the comparison this module has made since Phase 9 was already the deadline
    test. What it gained is the denominator `hints_used` never had.
    """

    def test_the_clock_was_already_graded_and_needed_no_second_comparison(
        self,
    ) -> None:
        """An interview that ran over its deadline is penalised by the existing
        estimate comparison, because they are the same number.
        """
        attempt, exercise = a_finished_attempt(
            minutes=25, estimated_minutes=20, mode=AttemptMode.INTERVIEW
        )
        assert attempt.policy.deadline_seconds == 20 * 60
        assert attempt.overran(attempt.started_at + timedelta(minutes=25)) is True

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.overran is True
        assert suggestion.grade is Grade.GOOD

    def test_an_interview_inside_its_deadline_is_penalised_for_nothing(self) -> None:
        attempt, exercise = a_finished_attempt(
            minutes=5, estimated_minutes=20, mode=AttemptMode.INTERVIEW
        )

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.overran is False
        assert suggestion.grade is Grade.EASY

    def test_no_hint_was_on_offer_so_using_none_was_not_a_choice(self) -> None:
        """The Phase 13 finding not repeated: `hints_used == 0` is true of every
        interview attempt and says nothing about the solver, so a surface needs
        the denominator to avoid printing it as restraint.
        """
        attempt, exercise = a_finished_attempt(mode=AttemptMode.INTERVIEW)

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.hints_used == 0
        assert suggestion.hints_offered == 0
        assert suggestion.declined_a_hint is False

    def test_a_practice_run_that_used_none_did_choose(self) -> None:
        attempt, exercise = a_finished_attempt()

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.hints_offered == 3
        assert suggestion.declined_a_hint is True

    def test_having_used_one_is_not_having_declined(self) -> None:
        attempt, exercise = a_finished_attempt(hints=1)

        suggestion = suggest_grade(attempt, exercise)

        assert suggestion.hints_offered == 3
        assert suggestion.declined_a_hint is False

    def test_the_denominator_is_the_policys_and_not_the_librarys(self) -> None:
        """An exercise edited mid-attempt cannot retroactively have offered a
        hint the policy was never built with (§4.3).
        """
        attempt, exercise = a_finished_attempt(mode=AttemptMode.INTERVIEW)
        assert exercise.hint_count == 3

        assert suggest_grade(attempt, exercise).hints_offered == 0

    def test_withholding_hints_does_not_make_a_clean_pass_cheaper(self) -> None:
        """The grade arithmetic is unchanged, deliberately. Revealing no hint is
        worth no penalty whether or not one was available.
        """
        interview, exercise = a_finished_attempt(mode=AttemptMode.INTERVIEW)
        practice, _ = a_finished_attempt()

        assert suggest_grade(interview, exercise).penalties == 0
        assert suggest_grade(practice, exercise).penalties == 0
        assert suggest_grade(interview, exercise).grade is Grade.EASY
