"""What makes a question representable, format by format.

The content suite only ever builds valid questions, so every refusal here is
exercised nowhere else. Each is a question that could never be passed, or
one whose answer is ambiguous, which is why they are invariants rather than
quality rules.
"""

from __future__ import annotations

from typing import Any

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.exercise import CounterExample
from practice.domain.quiz import (
    FixSuite,
    Option,
    Question,
    QuestionFormat,
    validate_identifier,
)

A = Option("alpha", "Alpha", "Because alpha.")
B = Option("beta", "Beta", "Because beta.")
C = Option("gamma", "Gamma", "Because gamma.")


def a_question(**overrides: Any) -> Question:
    fields: dict[str, Any] = {
        "id": "pick-one",
        "format": QuestionFormat.SINGLE,
        "label": "Pick one",
        "prompt": "Which one?",
        "options": (A, B),
        "answer": ("alpha",),
    }
    fields.update(overrides)
    return Question(**fields)


def test_a_well_formed_question_of_each_format_builds() -> None:
    a_question()
    a_question(format=QuestionFormat.MULTIPLE, options=(A, B, C), answer=("beta",))
    a_question(
        format=QuestionFormat.ORDER,
        options=(A, B, C),
        answer=("gamma", "alpha", "beta"),
    )
    a_question(
        format=QuestionFormat.LINE,
        options=(),
        snippet="one\ntwo",
        answer=("2",),
        explanation="Two.",
    )
    a_question(
        format=QuestionFormat.FIX,
        options=(),
        answer=(),
        explanation="Fixed.",
        fix=FixSuite(tests="t_tests.py"),
    )


@pytest.mark.parametrize("value", ["Pick", "pick_one", "pick--one", "-pick", ""])
def test_an_identifier_is_kebab_case(value: str) -> None:
    with pytest.raises(InvalidValueError, match="kebab-case"):
        validate_identifier(value, what="an id")


@pytest.mark.parametrize("field", ["label", "prompt"])
def test_a_question_says_what_it_asks(field: str) -> None:
    with pytest.raises(InvalidValueError, match=f"no {field}"):
        a_question(**{field: "  "})


@pytest.mark.parametrize("field", ["context", "explanation"])
def test_an_optional_text_is_written_or_left_out(field: str) -> None:
    with pytest.raises(InvalidValueError, match=f"blank {field}"):
        a_question(**{field: " "})


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", "A"), ("text", " "), ("why", " ")],
)
def test_an_option_has_an_id_text_and_a_reason(field: str, value: str) -> None:
    fields = {"id": "alpha", "text": "Alpha", "why": "Because."}
    fields[field] = value
    with pytest.raises(InvalidValueError):
        Option(**fields)


@pytest.mark.parametrize(
    ("fmt", "options"),
    [
        (QuestionFormat.SINGLE, (A,)),
        (QuestionFormat.MULTIPLE, (A, B)),
        (QuestionFormat.ORDER, (A, B)),
    ],
)
def test_a_choice_needs_enough_options(
    fmt: QuestionFormat, options: tuple[Option, ...]
) -> None:
    with pytest.raises(InvalidValueError, match="at least"):
        a_question(format=fmt, options=options, answer=("alpha",))


def test_option_ids_are_unique() -> None:
    with pytest.raises(InvalidValueError, match="repeats option"):
        a_question(options=(A, A))


def test_an_answer_names_an_option_it_offers() -> None:
    with pytest.raises(InvalidValueError, match="does not offer: delta"):
        a_question(answer=("delta",))


def test_an_answer_names_each_option_once() -> None:
    with pytest.raises(InvalidValueError, match="twice"):
        a_question(
            format=QuestionFormat.MULTIPLE, options=(A, B, C), answer=("alpha",) * 2
        )


@pytest.mark.parametrize("answer", [(), ("alpha", "beta")])
def test_a_single_choice_has_exactly_one_answer(answer: tuple[str, ...]) -> None:
    with pytest.raises(InvalidValueError, match="exactly one"):
        a_question(answer=answer)


def test_a_select_all_has_a_right_option() -> None:
    with pytest.raises(InvalidValueError, match="at least one right"):
        a_question(format=QuestionFormat.MULTIPLE, options=(A, B, C), answer=())


def test_an_order_places_every_option() -> None:
    with pytest.raises(InvalidValueError, match="places 2 of 3"):
        a_question(
            format=QuestionFormat.ORDER, options=(A, B, C), answer=("alpha", "beta")
        )


@pytest.mark.parametrize("fmt", [QuestionFormat.LINE, QuestionFormat.FIX])
def test_only_a_choice_offers_options(fmt: QuestionFormat) -> None:
    with pytest.raises(InvalidValueError, match="cannot offer options"):
        a_question(format=fmt, options=(A, B))


def a_line(**overrides: Any) -> Question:
    fields: dict[str, Any] = {
        "format": QuestionFormat.LINE,
        "options": (),
        "snippet": "one\ntwo\nthree",
        "answer": ("2",),
        "explanation": "Two.",
    }
    fields.update(overrides)
    return a_question(**fields)


def test_a_line_question_needs_a_snippet() -> None:
    with pytest.raises(InvalidValueError, match="needs a snippet"):
        a_line(snippet=None)


def test_a_line_question_explains_itself() -> None:
    with pytest.raises(InvalidValueError, match="needs an explanation"):
        a_line(explanation=None)


@pytest.mark.parametrize("answer", [(), ("2", "3"), ("two",)])
def test_a_line_question_is_answered_by_one_number(answer: tuple[str, ...]) -> None:
    with pytest.raises(InvalidValueError, match="one line number"):
        a_line(answer=answer)


@pytest.mark.parametrize("answer", ["0", "4"])
def test_a_line_answer_is_inside_the_snippet(answer: str) -> None:
    with pytest.raises(InvalidValueError, match="has 3"):
        a_line(answer=(answer,))


def test_a_line_question_numbers_its_lines() -> None:
    line = a_line()
    assert line.lines == ("one", "two", "three")
    assert line.line_count == 3
    assert a_question().lines == ()


def test_only_a_line_question_has_a_snippet() -> None:
    with pytest.raises(InvalidValueError, match="only a line question"):
        a_question(snippet="code")


def a_fix(**overrides: Any) -> Question:
    fields: dict[str, Any] = {
        "format": QuestionFormat.FIX,
        "options": (),
        "answer": (),
        "explanation": "Fixed.",
        "fix": FixSuite(tests="t_tests.py"),
    }
    fields.update(overrides)
    return a_question(**fields)


def test_a_fix_question_needs_its_tests() -> None:
    with pytest.raises(InvalidValueError, match="needs a tests file"):
        a_fix(fix=None)


def test_a_fix_question_is_answered_by_code_not_a_key() -> None:
    with pytest.raises(InvalidValueError, match="not by a key"):
        a_fix(answer=("alpha",))


def test_a_fix_question_explains_itself() -> None:
    with pytest.raises(InvalidValueError, match="needs an explanation"):
        a_fix(explanation=None)


def test_only_a_fix_question_carries_a_suite() -> None:
    with pytest.raises(InvalidValueError, match="cannot carry a test suite"):
        a_question(fix=FixSuite(tests="t_tests.py"))


@pytest.mark.parametrize(
    ("tests", "limit", "match"),
    [(" ", 10, "tests file"), ("t_tests.py", 0, "at least 1")],
)
def test_a_fix_suite_has_tests_and_a_time_limit(
    tests: str, limit: int, match: str
) -> None:
    with pytest.raises(InvalidValueError, match=match):
        FixSuite(tests=tests, time_limit_seconds=limit)


def test_a_fix_suite_names_every_file_it_needs() -> None:
    suite = FixSuite(
        tests="t_tests.py",
        counter_examples=(CounterExample("wrong.py", frozenset({"a-test"})),),
    )
    assert suite.files == ("t_tests.py", "wrong.py")


def test_an_option_is_found_by_id_or_not_at_all() -> None:
    question = a_question()
    assert question.option("beta") is B
    assert question.option("delta") is None


def test_only_the_choice_formats_have_options() -> None:
    assert {fmt for fmt in QuestionFormat if fmt.has_options} == {
        QuestionFormat.SINGLE,
        QuestionFormat.MULTIPLE,
        QuestionFormat.ORDER,
    }
