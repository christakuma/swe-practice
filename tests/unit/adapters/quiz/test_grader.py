"""`QuizGrader` against a canned runner: the order of reports, and a fix's.

The choice questions are graded by the domain and tested there; what is left
here is what the adapter adds -- reading the sheet from the log, putting every
question's reports in the order asked, and turning a fix question's run into
reports named after the question. `StubKataRunner` stands in for pytest, so a
suite that never ran costs a millisecond rather than a time limit.
"""

from __future__ import annotations

import pytest

from practice.adapters.kata.pytest_runner import TestOutcome
from practice.adapters.quiz import QuizGrader, QuizGraderError
from practice.domain.attempt import Attempt, AttemptPolicy
from practice.domain.ids import AttemptId
from practice.domain.quiz import Answer, render_sheet
from practice.domain.verdict import Outcome
from tests.fakes import (
    FakeClock,
    FakeWorkspace,
    StubKataRunner,
    a_kata,
    a_quiz,
    a_quiz_spec,
    a_record,
    a_run,
)
from tests.fakes.kata import a_timeout

QUIZ = a_quiz(with_fix=True)
SPEC = a_quiz_spec()
FIX = "def transfer(source, target, amount):\n    pass"

RIGHT = {
    "which-line": Answer(values=("1",)),
    "which-condition": Answer(values=("circular-wait",)),
    "which-checks": Answer(values=("lock-graph", "lockdep")),
    "which-steps": Answer(values=("add", "copy", "drop")),
    "fix-it": Answer(code=FIX),
}


def an_attempt(sheet: str | None) -> Attempt:
    clock = FakeClock()
    attempt = Attempt(
        attempt_id=AttemptId.parse("aabbccdd-0000-4000-8000-000000000025"),
        exercise_id=QUIZ.id,
        policy=AttemptPolicy.for_exercise(QUIZ),
        started_at=clock.now(),
    )
    if sheet is not None:
        attempt.save_solution(sheet, at=clock.now())
    return attempt


def sheet(**answers: Answer) -> str:
    return render_sheet(QUIZ.title, SPEC.questions, {**RIGHT, **answers})


def test_every_question_is_reported_in_the_order_asked() -> None:
    runner = StubKataRunner(a_run(a_record("test_sorted", doc="Locks are sorted.")))
    verdict = QuizGrader(runner).grade(QUIZ, FakeWorkspace(), an_attempt(sheet()))

    assert [report.check_id for report in verdict.reports] == [
        "which-line",
        "which-condition",
        "which-checks",
        "which-steps",
        "fix-it/sorted",
    ]
    assert verdict.outcome is Outcome.PASS


def test_a_fix_runs_its_own_suite_on_the_code_under_its_heading() -> None:
    runner = StubKataRunner(a_run(a_record("test_sorted")))
    QuizGrader(runner).grade(QUIZ, FakeWorkspace(), an_attempt(sheet()))
    assert runner.calls == [("ledger_tests.py", FIX)]


def test_a_fix_test_is_labelled_with_its_question() -> None:
    runner = StubKataRunner(
        a_run(
            a_record(
                "test_sorted",
                outcome=TestOutcome.FAILED,
                doc="Locks are sorted.",
                message="cycle",
            )
        )
    )
    verdict = QuizGrader(runner).grade(QUIZ, FakeWorkspace(), an_attempt(sheet()))
    (failure,) = verdict.failures
    assert failure.check_id == "fix-it/sorted"
    assert failure.label == "Your fix: Locks are sorted."
    assert failure.explanation == "cycle"


def test_a_wrong_choice_fails_the_attempt_with_the_fix_passing() -> None:
    runner = StubKataRunner(a_run(a_record("test_sorted")))
    wrong = sheet(**{"which-condition": Answer(values=("hold-and-wait",))})
    verdict = QuizGrader(runner).grade(QUIZ, FakeWorkspace(), an_attempt(wrong))
    assert [report.check_id for report in verdict.failures] == ["which-condition"]


@pytest.mark.parametrize(
    "answer", [Answer(code=""), Answer(code="  \n  ")], ids=["empty", "blank"]
)
def test_a_fix_with_no_code_is_one_failure_and_no_run(answer: Answer) -> None:
    runner = StubKataRunner(a_run(a_record("test_sorted")))
    verdict = QuizGrader(runner).grade(
        QUIZ, FakeWorkspace(), an_attempt(sheet(**{"fix-it": answer}))
    )
    (failure,) = verdict.failures
    assert failure.check_id == "fix-it/answered"
    assert failure.explanation == "There is no code under `## fix-it` in the sheet."
    assert runner.calls == []


def test_a_fix_heading_with_no_block_says_so() -> None:
    text = sheet().replace("```python", "Ran out of time.\n\n<!--", 1)
    text = text.replace("\n```\n", "\n-->\n", 1)
    runner = StubKataRunner(a_run(a_record("test_sorted")))
    verdict = QuizGrader(runner).grade(QUIZ, FakeWorkspace(), an_attempt(text))
    (failure,) = verdict.failures
    assert failure.check_id == "fix-it/answered"
    assert failure.explanation == "There is no code block under `## fix-it`."


def test_a_suite_that_never_ran_is_one_failure_that_says_why() -> None:
    runner = StubKataRunner(a_timeout(output="killed"))
    verdict = QuizGrader(runner).grade(QUIZ, FakeWorkspace(), an_attempt(sheet()))
    (failure,) = verdict.failures
    assert failure.check_id == "fix-it/suite-ran"
    assert failure.actual == "the test suite was killed after 10s without finishing"
    assert failure.explanation == "killed"


def test_a_suite_that_never_ran_and_said_nothing_has_no_explanation() -> None:
    runner = StubKataRunner(a_timeout())
    verdict = QuizGrader(runner).grade(QUIZ, FakeWorkspace(), an_attempt(sheet()))
    assert verdict.failures[0].explanation is None


def test_an_attempt_with_no_sheet_is_a_programming_error() -> None:
    runner = StubKataRunner(a_run())
    with pytest.raises(QuizGraderError, match="saved no answers"):
        QuizGrader(runner).grade(QUIZ, FakeWorkspace(), an_attempt(None))


def test_anything_but_a_quiz_is_refused() -> None:
    runner = StubKataRunner(a_run())
    with pytest.raises(QuizGraderError, match="does not know how to read"):
        QuizGrader(runner).grade(a_kata(), FakeWorkspace(), an_attempt(sheet()))
