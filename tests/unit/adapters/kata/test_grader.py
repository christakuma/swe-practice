"""Test results become check reports.

Every case here runs against `StubKataRunner`, so the whole file is milliseconds
and includes the two cases a real subprocess makes expensive: a suite killed by
the time limit, and a suite that collected nothing. That is the `KataRunner`
protocol earning its keep on the day it was written (PLAN.md §13).

What is deliberately *not* here is whether pytest produces the records this file
feeds in. That is `tests/integration/kata/`, and the split is the usual one: the
mapping is logic and the invocation is I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.kata.grader import (
    COMPLEXITY_CHECK_ID,
    SUITE_CHECK_ID,
    KataGrader,
    KataRunnerError,
    check_id_for,
    complexity_report,
    label_for,
    latest_source,
)
from practice.adapters.kata.pytest_runner import KataRun, TestOutcome
from practice.domain.attempt import (
    Attempt,
    AttemptPolicy,
    ComplexityClaim,
)
from practice.domain.exercise import (
    CheckSpec,
    ComplexityExpectation,
    Difficulty,
    Exercise,
    ExerciseKind,
    GitScenarioSpec,
    Hint,
    KataSpec,
)
from practice.domain.ids import AttemptId, ExerciseId, tag
from practice.domain.verdict import Outcome, Severity
from tests.fakes import FakeClock, FakeWorkspace, StubKataRunner, a_record, a_run
from tests.fakes.kata import a_timeout

if TYPE_CHECKING:
    from practice.domain.ports import Grader

SOURCE = "def two_sum(numbers, target):\n    return (0, 1)\n"


def a_kata(complexity: ComplexityExpectation | None = None) -> Exercise:
    return Exercise(
        id=ExerciseId("katas/two-sum"),
        kind=ExerciseKind.KATA,
        title="Two Sum",
        prompt="Find the pair.",
        difficulty=Difficulty.EASY,
        tags=(tag("arrays"),),
        estimated_minutes=15,
        hints=(Hint("Trade space for time."),),
        notes="Why a dict.",
        spec=KataSpec(
            language="python",
            stub="stub.py",
            tests="tests.py",
            reference="solution.py",
            complexity=complexity,
        ),
    )


def an_attempt(
    exercise: Exercise,
    *,
    source: str | None = SOURCE,
    claim: ComplexityClaim | None = None,
) -> Attempt:
    clock = FakeClock()
    attempt = Attempt(
        attempt_id=AttemptId.parse("aabbccdd-0000-4000-8000-000000000001"),
        exercise_id=exercise.id,
        policy=AttemptPolicy.for_exercise(exercise),
        started_at=clock.now(),
    )
    if source is not None:
        attempt.save_solution(source, at=clock.now())
    if claim is not None:
        attempt.declare_complexity(claim)
    return attempt


def verdict_for(
    run: KataRun,
    *,
    complexity: ComplexityExpectation | None = None,
    claim: ComplexityClaim | None = None,
    source: str | None = SOURCE,
) -> tuple[KataGrader, Exercise, Attempt]:
    """Assemble the three arguments `Grader.grade` takes."""
    exercise = a_kata(complexity)
    return (
        KataGrader(StubKataRunner(run)),
        exercise,
        an_attempt(exercise, source=source, claim=claim),
    )


# --- the port --------------------------------------------------------------


def test_the_kata_grader_satisfies_the_grader_port() -> None:
    """mypy is the real assertion, as in `test_ports.py`: the annotation is
    what fails under `--strict` if the adapter drifts out of shape.
    """
    grader: Grader = KataGrader(StubKataRunner(a_run(a_record("test_one"))))
    exercise = a_kata()

    verdict = grader.grade(exercise, FakeWorkspace(), an_attempt(exercise))

    assert verdict.outcome is Outcome.PASS


# --- one test, one check ---------------------------------------------------


def test_every_test_becomes_a_required_check() -> None:
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one"), a_record("test_two"))
    )

    verdict = grader.grade(exercise, FakeWorkspace(), attempt)

    assert [report.check_id for report in verdict.reports] == ["one", "two"]
    assert all(report.severity is Severity.REQUIRED for report in verdict.reports)


def test_a_failing_test_fails_the_verdict() -> None:
    grader, exercise, attempt = verdict_for(
        a_run(
            a_record("test_one"),
            a_record(
                "test_two",
                outcome=TestOutcome.FAILED,
                message="assert (0, 0) == (1, 2)",
                location="solution.py:4",
            ),
        )
    )

    verdict = grader.grade(exercise, FakeWorkspace(), attempt)

    assert verdict.outcome is Outcome.FAIL
    failure = verdict.failures[0]
    assert failure.check_id == "two"
    assert failure.actual == "failed at solution.py:4"
    assert failure.explanation == "assert (0, 0) == (1, 2)"


def test_a_passing_check_carries_no_explanation() -> None:
    """A message on a pass would be printed under a green line, where there is
    nothing to act on — the CLI prints the explanation of a failure only.
    """
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one", message="ignored"))
    )

    report = grader.grade(exercise, FakeWorkspace(), attempt).reports[0]

    assert report.passed
    assert report.explanation is None
    assert report.actual == "passed"


def test_an_error_in_setup_is_distinguished_from_a_failure() -> None:
    """Different files to go looking in: a failure is a wrong solution, an error
    is a broken suite.
    """
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one", outcome=TestOutcome.ERROR))
    )

    assert grader.grade(exercise, FakeWorkspace(), attempt).reports[0].actual == "error"


def test_a_skipped_test_does_not_count_as_passed() -> None:
    """A hidden suite that skips has not verified what it claims to, and calling
    that satisfied would quietly narrow what the kata grades.
    """
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one", outcome=TestOutcome.SKIPPED))
    )

    assert grader.grade(exercise, FakeWorkspace(), attempt).outcome is Outcome.FAIL


def test_the_docstring_is_the_label() -> None:
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one", doc="Finds the two positions.\n\nMore prose.\n"))
    )

    assert (
        grader.grade(exercise, FakeWorkspace(), attempt).reports[0].label
        == "Finds the two positions."
    )


def test_two_tests_whose_ids_collide_both_reach_the_verdict() -> None:
    """`Verdict` refuses duplicate check ids, and a parametrized suite produces
    names that differ only in characters an id cannot hold — `[a.b]` and `[a-b]`
    both slug to `one-a-b`. Dropping one would mean a test whose result silently
    never reached the verdict.
    """
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one[a.b]"), a_record("test_one[a-b]"))
    )

    verdict = grader.grade(exercise, FakeWorkspace(), attempt)

    assert [report.check_id for report in verdict.reports] == [
        "one-a-b",
        "one-a-b-2",
    ]


# --- a suite that did not run ----------------------------------------------


def test_a_timed_out_suite_is_one_failing_check_not_none() -> None:
    """`Verdict` cannot be built empty, and "every test failed" would be a lie:
    a timeout says nothing about any individual assertion.
    """
    grader, exercise, attempt = verdict_for(a_timeout(output="Timed out after 10s"))

    verdict = grader.grade(exercise, FakeWorkspace(), attempt)

    assert verdict.outcome is Outcome.FAIL
    assert [report.check_id for report in verdict.reports] == [SUITE_CHECK_ID]
    assert "killed after 10s" in (verdict.reports[0].actual or "")
    assert verdict.reports[0].explanation == "Timed out after 10s"


def test_a_suite_that_collected_nothing_says_so() -> None:
    grader, exercise, attempt = verdict_for(
        KataRun(tests=(), exit_code=2, exit_status=2, output="ERROR tests.py")
    )

    report = grader.grade(exercise, FakeWorkspace(), attempt).reports[0]

    assert report.check_id == SUITE_CHECK_ID
    assert "collected no tests" in (report.actual or "")


def test_a_run_that_wrote_no_report_is_reported_as_such() -> None:
    """The report file is missing or unparseable — killed mid-write, or written
    by an older copy of the plugin in a resumed workspace.
    """
    grader, exercise, attempt = verdict_for(KataRun(tests=(), exit_code=1))

    report = grader.grade(exercise, FakeWorkspace(), attempt).reports[0]

    assert "wrote no report" in (report.actual or "")


# --- the complexity claim --------------------------------------------------


def test_a_matching_claim_is_a_clean_pass() -> None:
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one")),
        complexity=ComplexityExpectation(expected_time="O(n)", expected_space="O(n)"),
        claim=ComplexityClaim(time="O(n)", space="O(n)"),
    )

    verdict = grader.grade(exercise, FakeWorkspace(), attempt)

    assert verdict.outcome is Outcome.PASS
    assert verdict.reports[-1].check_id == COMPLEXITY_CHECK_ID


def test_a_disagreeing_claim_passes_with_an_advisory() -> None:
    """The §4.4 feature: you achieved the goal, and here is what to reconcile.
    Never a failure — the tool does not analyse asymptotics (PLAN.md §7).
    """
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one")),
        complexity=ComplexityExpectation(expected_time="O(n)", expected_space="O(n)"),
        claim=ComplexityClaim(time="O(n^2)", space="O(1)"),
    )

    verdict = grader.grade(exercise, FakeWorkspace(), attempt)

    assert verdict.outcome is Outcome.PASS_WITH_ADVISORIES
    advisory = verdict.advisories[0]
    assert advisory.expected == "time O(n), space O(n)"
    assert advisory.actual == "time O(n^2), space O(1)"


def test_declining_to_declare_is_itself_the_advisory() -> None:
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one")),
        complexity=ComplexityExpectation(expected_time="O(n)", expected_space="O(n)"),
    )

    verdict = grader.grade(exercise, FakeWorkspace(), attempt)

    assert verdict.outcome is Outcome.PASS_WITH_ADVISORIES
    assert verdict.advisories[0].actual == "not declared"


def test_an_exercise_with_no_expectation_gets_no_complexity_check() -> None:
    """Inventing one would fail every attempt at an exercise whose author simply
    did not state a cost.
    """
    grader, exercise, attempt = verdict_for(
        a_run(a_record("test_one")), claim=ComplexityClaim(time="O(n)", space="O(n)")
    )

    verdict = grader.grade(exercise, FakeWorkspace(), attempt)

    assert [report.check_id for report in verdict.reports] == ["one"]


def test_the_complexity_report_is_optional_at_the_function_level() -> None:
    assert complexity_report(None, ComplexityClaim(time="O(n)", space="O(n)")) is None


# --- what the grader refuses ----------------------------------------------


def test_it_refuses_an_attempt_that_saved_no_solution() -> None:
    """A programming error — a use case that graded before saving — so an
    exception rather than a failing check the solver cannot act on.
    """
    grader, exercise, attempt = verdict_for(a_run(a_record("test_one")), source=None)

    with pytest.raises(KataRunnerError, match="saved no solution"):
        grader.grade(exercise, FakeWorkspace(), attempt)


def test_it_refuses_an_exercise_that_is_not_a_kata() -> None:
    """The registry refuses first in practice; this is the backstop, because an
    adapter that trusts its caller's dispatch has no way to say what went wrong.
    """
    scenario = Exercise(
        id=ExerciseId("git/revert-a-pushed-commit"),
        kind=ExerciseKind.GIT_SCENARIO,
        title="Revert a pushed commit",
        prompt="Undo it without rewriting published history.",
        difficulty=Difficulty.MEDIUM,
        tags=(),
        estimated_minutes=20,
        hints=(),
        notes="",
        spec=GitScenarioSpec(
            fixture="fixture.sh",
            reference="solution.cmds",
            checks=(
                CheckSpec(
                    id="history-preserved",
                    label="The commit is still reachable.",
                    severity=Severity.REQUIRED,
                    assertion="is_ancestor",
                ),
            ),
            allowed_commands=frozenset({"git"}),
        ),
    )
    grader = KataGrader(StubKataRunner(a_run(a_record("test_one"))))

    with pytest.raises(KataRunnerError, match="does not know how to run"):
        grader.grade(scenario, FakeWorkspace(), an_attempt(scenario))


# --- the pure helpers ------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("test_handles_repeated_values", "handles-repeated-values"),
        ("test_two_sum", "two-sum"),
        ("test_one[a-b]", "one-a-b"),
        ("test_", "test"),
        # A class-based suite keeps the class, so two `test_empty` methods on
        # different classes do not collapse into one check.
        ("TestSorting::test_empty", "testsorting-test-empty"),
    ],
)
def test_check_ids_are_kebab_case(name: str, expected: str) -> None:
    assert check_id_for(a_record(name)) == expected


def test_a_test_with_no_docstring_still_gets_a_readable_label() -> None:
    assert label_for(a_record("test_handles_negatives")) == "handles negatives"


def test_a_whitespace_only_docstring_falls_back_to_the_name() -> None:
    assert label_for(a_record("test_one", doc="   \n  \n")) == "one"


def test_the_latest_saved_source_is_the_one_graded() -> None:
    """A solver saves repeatedly while working; what is graded is where they
    stopped. The earlier snapshots stay in the log for replay.
    """
    exercise = a_kata()
    attempt = an_attempt(exercise, source="first")
    attempt.save_solution("second", at=FakeClock().now())

    assert latest_source(attempt) == "second"
