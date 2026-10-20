"""One question, one check: what passes, and what each failure says.

What a failure *says* is the design (`grading.py`): why the chosen option is
wrong, never which is right. So most cases here assert on the explanation,
and every failing one asserts that `expected` is empty.
"""

from __future__ import annotations

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.quiz import Answer, Question, grade
from practice.domain.verdict import CheckReport, Severity
from tests.fakes import a_quiz_spec

SPEC = a_quiz_spec()


def question(question_id: str) -> Question:
    return SPEC.question(question_id)


def failed(question_id: str, *values: str) -> CheckReport:
    report = grade(question(question_id), Answer(values=values))
    assert not report.passed
    assert report.expected is None
    assert report.severity is Severity.REQUIRED
    return report


def why(report: CheckReport) -> str:
    assert report.explanation is not None
    return report.explanation


@pytest.mark.parametrize(
    ("question_id", "values"),
    [
        ("which-condition", ("circular-wait",)),
        ("which-checks", ("lockdep", "lock-graph")),
        ("which-steps", ("add", "copy", "drop")),
        ("which-line", ("1",)),
        ("which-line", ("01",)),
    ],
)
def test_the_exact_answer_passes_without_an_explanation(
    question_id: str, values: tuple[str, ...]
) -> None:
    report = grade(question(question_id), Answer(values=values))
    assert report.passed
    assert report.check_id == question_id
    assert report.label == question(question_id).label
    assert report.explanation is None


@pytest.mark.parametrize("answer", [None, Answer(), Answer(values=())])
def test_an_unanswered_question_fails_and_says_so(answer: Answer | None) -> None:
    report = grade(question("which-condition"), answer)
    assert not report.passed
    assert why(report) == "Not answered."


def test_a_problem_with_the_sheet_is_the_explanation() -> None:
    report = grade(question("which-condition"), Answer(problem="answered twice"))
    assert why(report) == "answered twice"


def test_a_wrong_choice_says_why_that_choice_is_wrong() -> None:
    report = failed("which-condition", "hold-and-wait")
    assert why(report) == "You chose `hold-and-wait`: Still held."
    assert "circular" not in why(report).lower()


def test_an_option_that_does_not_exist_is_named() -> None:
    assert "no option `delta`" in why(failed("which-condition", "delta"))


def test_a_choice_given_twice_is_named() -> None:
    assert "more than once" in why(failed("which-checks", "lockdep", "lockdep"))


def test_a_single_choice_takes_one_answer() -> None:
    report = failed("which-condition", "circular-wait", "hold-and-wait")
    assert "takes one answer, and 2 were given" in why(report)


def test_a_select_all_explains_every_wrong_choice() -> None:
    report = failed("which-checks", "lock-graph", "load-test")
    assert why(report) == "You chose `load-test`: Only by luck."


def test_a_select_all_that_stops_short_says_there_is_more() -> None:
    report = failed("which-checks", "lock-graph")
    assert why(report) == "Everything you chose is right, and there is more to choose."


def test_a_wrong_line_is_named_without_the_right_one() -> None:
    assert why(failed("which-line", "2")) == "Line 2 is not the one."


@pytest.mark.parametrize("value", ["9", "0", "two"])
def test_a_line_outside_the_snippet_is_named(value: str) -> None:
    assert "runs from 1 to 3" in why(failed("which-line", value))


def test_a_line_question_takes_one_number() -> None:
    assert "2 were given" in why(failed("which-line", "1", "2"))


def test_an_order_says_where_it_first_goes_wrong() -> None:
    report = failed("which-steps", "add", "drop", "copy")
    assert why(report) == "Step 2 is the first one out of place."


def test_an_order_with_an_unknown_step_names_it() -> None:
    assert "no step `rename`" in why(failed("which-steps", "add", "rename", "drop"))


def test_an_order_that_misses_or_repeats_a_step_names_both() -> None:
    report = failed("which-steps", "add", "add", "drop")
    assert why(report) == (
        "An order places every step exactly once: `copy` is not placed; "
        "`add` is placed twice."
    )


def test_an_order_that_only_misses_a_step_says_so() -> None:
    assert why(failed("which-steps", "add", "drop")).endswith("`copy` is not placed.")


def test_a_fix_question_is_its_suites_to_grade() -> None:
    with pytest.raises(InvalidValueError, match="test suite grades"):
        grade(question("fix-it"), Answer(code="x = 1"))


def test_an_order_that_only_repeats_a_step_says_so() -> None:
    report = failed("which-steps", "add", "copy", "drop", "add")
    assert (
        why(report) == "An order places every step exactly once: `add` is placed twice."
    )
