"""The order options are shown in, and the text the terminal and tutor read."""

from __future__ import annotations

from practice.domain.quiz import (
    QuestionFormat,
    answer_key_text,
    presented_options,
    statement_text,
)
from tests.fakes import a_quiz_spec

SPEC = a_quiz_spec()


def ids(options: tuple[object, ...]) -> list[str]:
    return [option.id for option in options]  # type: ignore[attr-defined]


def test_the_order_is_a_function_of_the_attempt() -> None:
    question = SPEC.question("which-checks")
    first = presented_options(question, "attempt-1")
    assert presented_options(question, "attempt-1") == first
    assert sorted(ids(first)) == sorted(ids(question.options))


def test_different_attempts_see_different_orders() -> None:
    question = SPEC.question("which-checks")
    orders = {
        tuple(ids(presented_options(question, f"attempt-{n}"))) for n in range(40)
    }
    assert len(orders) > 1


def test_an_order_question_is_never_shown_in_its_answer() -> None:
    question = SPEC.question("which-steps")
    shown = [tuple(ids(presented_options(question, f"seed-{n}"))) for n in range(200)]
    assert question.answer not in shown
    assert all(sorted(order) == sorted(question.answer) for order in shown)


def test_the_statement_asks_every_question_and_answers_none() -> None:
    text = statement_text(SPEC.questions)
    assert "Question 1 of 5 (which-line)" in text
    assert "  1 | with source.lock:" in text
    assert "  circular-wait  Circular wait" in text
    assert "Answer on the line `which-checks:` in answers.md" in text
    assert "every option id that applies" in text
    assert "Answer with code, in the block under `## fix-it`" in text
    assert "Four conditions." in text
    for question in SPEC.questions:
        for option in question.options:
            assert option.why not in text
        if question.explanation is not None:
            assert question.explanation not in text


def test_the_statement_skips_a_context_that_is_not_there() -> None:
    bare = SPEC.question("which-condition")
    without = type(bare)(
        id=bare.id,
        format=bare.format,
        label=bare.label,
        prompt=bare.prompt,
        options=bare.options,
        answer=bare.answer,
    )
    assert statement_text((without,)).splitlines()[:3] == [
        "Question 1 of 1 (which-condition)",
        "",
        "Which condition does a fixed order remove?",
    ]


def test_the_key_says_every_answer_and_every_reason() -> None:
    text = answer_key_text(SPEC.questions)
    assert "1. The line that took the lock (which-line)\nAnswer: line 1" in text
    assert "Answer: lock-graph, lockdep" in text
    assert "- circular-wait (right): Circular wait\n  No cycle can form." in text
    assert "- hold-and-wait (wrong): Hold and wait\n  Still held." in text
    assert "Sort by id." in text
    fix = SPEC.question("fix-it")
    assert fix.format is QuestionFormat.FIX
    assert "5. Your fix (fix-it)\nSort by id." in text
