"""`QuizSpec`'s invariants, its clause in `editable_source`, and its statement.

As with `ContainerSpec`, the content suite only builds valid specs, so the
refusals are exercised here or nowhere.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.exercise import (
    CounterExample,
    EditableSource,
    ExerciseKind,
    QuizSpec,
    editable_source,
)
from practice.domain.quiz import FixSuite
from tests.fakes import a_quiz, a_quiz_spec

QUIZ = a_quiz(with_fix=True)
SPEC = a_quiz_spec()


def a_spec(**overrides: Any) -> QuizSpec:
    return dataclasses.replace(SPEC, **overrides)


def test_it_is_a_quiz_edited_as_markdown() -> None:
    assert SPEC.kind is ExerciseKind.QUIZ
    assert SPEC.language == "markdown"
    assert editable_source(SPEC) == EditableSource(
        filename="answers.md", language="markdown", reference="solution.md"
    )


@pytest.mark.parametrize("field", ["stub", "reference"])
def test_both_sheets_are_named(field: str) -> None:
    with pytest.raises(InvalidValueError, match=f"needs a {field}"):
        a_spec(**{field: " "})


def test_a_sheet_is_a_name_not_a_path() -> None:
    with pytest.raises(InvalidValueError, match="cannot be a path"):
        a_spec(reference="../solution.md")


def test_the_stub_is_called_what_the_instructions_call_it() -> None:
    with pytest.raises(InvalidValueError, match=r"answered in answers\.md"):
        a_spec(stub="sheet.md")


def test_a_quiz_asks_something() -> None:
    with pytest.raises(InvalidValueError, match="at least one question"):
        a_spec(questions=())


def test_question_ids_are_unique() -> None:
    with pytest.raises(InvalidValueError, match="duplicate question ids: which-line"):
        a_spec(questions=(*SPEC.questions, SPEC.question("which-line")))


def test_a_fix_suites_tests_are_a_name_too() -> None:
    """The provisioner copies them into the workspace by this name."""
    escaping = dataclasses.replace(
        SPEC.question("fix-it"), fix=FixSuite(tests="../ledger_tests.py")
    )
    with pytest.raises(InvalidValueError, match=r"fix 'fix-it'.*cannot be a path"):
        a_spec(questions=(escaping,))


def test_a_constraint_is_never_blank() -> None:
    with pytest.raises(InvalidValueError, match="constraint cannot be blank"):
        a_spec(constraints=(" ",))


def test_it_names_every_file_beside_it() -> None:
    fix = SPEC.question("fix-it")
    with_counter = dataclasses.replace(
        fix,
        fix=FixSuite(
            tests="ledger_tests.py",
            counter_examples=(CounterExample("one-lock.py", frozenset({"a"})),),
        ),
    )
    spec = a_spec(questions=(*SPEC.questions[:-1], with_counter))
    assert spec.referenced_files == (
        "answers.md",
        "solution.md",
        "ledger_tests.py",
        "one-lock.py",
    )
    assert spec.fixes == (with_counter,)


def test_a_question_is_found_by_id_or_refused() -> None:
    assert SPEC.question("which-line").id == "which-line"
    with pytest.raises(InvalidValueError, match="no such question"):
        SPEC.question("which-hat")


def test_the_statement_has_the_constraints_and_the_questions() -> None:
    statement = QUIZ.statement
    assert statement.startswith("Transfers freeze a few times an hour.")
    assert "Constraints:\n- 16 worker threads.\n- Account ids are unique." in statement
    assert "Question 5 of 5 (fix-it)" in statement


def test_a_quiz_without_constraints_lists_none() -> None:
    bare = dataclasses.replace(QUIZ, spec=a_spec(constraints=()))
    assert "Constraints:" not in bare.statement
