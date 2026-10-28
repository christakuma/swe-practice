"""`answers.md`, read and written: the grammar, and what it forgives.

The sheet is the only thing a quiz's verdict is computed from, so every rule
in `sheet.py`'s docstring has a case here: what counts as an answer, what is
prose, how a fence opens and closes, and what a sheet says about a question
it cannot be graded on.
"""

from __future__ import annotations

from practice.domain.quiz import Answer, parse_sheet, render_sheet
from tests.fakes import a_quiz_spec

QUESTIONS = a_quiz_spec().questions


def test_an_answer_line_is_read_and_lowercased() -> None:
    answers = parse_sheet("which-condition: Circular-Wait\n", QUESTIONS)
    assert answers == {"which-condition": Answer(values=("circular-wait",))}


def test_several_values_are_split_on_commas_and_blanks_dropped() -> None:
    answers = parse_sheet("which-checks: lock-graph , ,lockdep,\n", QUESTIONS)
    assert answers["which-checks"].values == ("lock-graph", "lockdep")


def test_an_empty_answer_line_is_blank() -> None:
    answers = parse_sheet("which-line:\n", QUESTIONS)
    assert answers["which-line"].is_blank


def test_prose_that_looks_like_an_answer_is_ignored() -> None:
    """`Note: ...` is prose, not an answer to a question called `note`."""
    assert parse_sheet("note: remember the dump\n", QUESTIONS) == {}


def test_a_question_answered_twice_is_a_problem_not_a_choice() -> None:
    answers = parse_sheet("which-line: 1\nwhich-line: 2\n", QUESTIONS)
    assert answers["which-line"].problem is not None
    assert "two lines" in answers["which-line"].problem


def test_a_fix_is_the_first_block_under_its_heading() -> None:
    sheet = "## fix-it\n\nSome prose.\n\n```python\nx = 1\n```\n\n```\ny = 2\n```\n"
    answers = parse_sheet(sheet, QUESTIONS)
    assert answers == {"fix-it": Answer(code="x = 1")}


def test_ids_are_read_case_blind_on_answer_lines_and_headings_alike() -> None:
    """Both or neither: a sheet that read `Which-Condition:` and ignored
    `## Fix-It` graded the fix as unanswered, with nothing to say why.
    """
    sheet = "Which-Condition: circular-wait\n\n## Fix-It\n\n```\nx = 1\n```\n"
    answers = parse_sheet(sheet, QUESTIONS)
    assert answers == {
        "which-condition": Answer(values=("circular-wait",)),
        "fix-it": Answer(code="x = 1"),
    }


def test_a_heading_with_no_block_under_it_is_a_problem() -> None:
    answers = parse_sheet("## fix-it\n\nI ran out of time.\n", QUESTIONS)
    assert answers["fix-it"].problem is not None
    assert "no code block" in answers["fix-it"].problem


def test_a_heading_for_something_else_takes_no_block() -> None:
    assert parse_sheet("## notes\n\n```\nx = 1\n```\n", QUESTIONS) == {}


def test_answer_lines_inside_a_block_are_code_not_answers() -> None:
    sheet = "## fix-it\n\n```python\nwhich-line: 3\n```\n"
    answers = parse_sheet(sheet, QUESTIONS)
    assert "which-line" not in answers
    assert answers["fix-it"].code == "which-line: 3"


def test_a_tilde_fence_and_a_longer_closer_are_fences() -> None:
    sheet = "## fix-it\n\n~~~\nx = 1\n~~~~~\n"
    assert parse_sheet(sheet, QUESTIONS)["fix-it"].code == "x = 1"


def test_a_shorter_run_does_not_close_a_longer_fence() -> None:
    sheet = "## fix-it\n\n````python\n```\nx = 1\n````\n"
    assert parse_sheet(sheet, QUESTIONS)["fix-it"].code == "```\nx = 1"


def test_an_unclosed_fence_runs_to_the_end() -> None:
    sheet = "## fix-it\n\n```python\nx = 1\ny = 2\n"
    assert parse_sheet(sheet, QUESTIONS)["fix-it"].code == "x = 1\ny = 2"


def test_a_blank_answer_has_nothing_in_it() -> None:
    assert Answer().is_blank
    assert Answer(code="   ").is_blank
    assert not Answer(values=("a",)).is_blank
    assert not Answer(code="x").is_blank
    assert not Answer(problem="twice").is_blank


def test_a_rendered_sheet_reads_back_as_what_was_rendered() -> None:
    answers = {
        "which-line": Answer(values=("1",)),
        "which-condition": Answer(values=("circular-wait",)),
        "which-checks": Answer(values=("lock-graph", "lockdep")),
        "which-steps": Answer(values=("add", "copy", "drop")),
        "fix-it": Answer(code="def transfer():\n    pass"),
    }
    sheet = render_sheet("Transfers", QUESTIONS, answers)
    assert parse_sheet(sheet, QUESTIONS) == answers
    assert render_sheet("Transfers", QUESTIONS, parse_sheet(sheet, QUESTIONS)) == sheet


def test_an_unanswered_question_renders_as_its_id_and_a_colon() -> None:
    sheet = render_sheet("Transfers", QUESTIONS, {})
    assert "\nwhich-line:\n" in sheet
    assert "## fix-it\n\n```python\n\n```" in sheet
    assert sheet.startswith("# Transfers: your answers\n")


def test_code_with_a_fence_in_it_gets_a_longer_fence() -> None:
    code = 'DOC = """\n```\nexample\n```\n"""'
    sheet = render_sheet("Transfers", QUESTIONS, {"fix-it": Answer(code=code)})
    assert "````python" in sheet
    assert parse_sheet(sheet, QUESTIONS)["fix-it"].code == code


def test_a_sheet_with_no_choice_questions_has_no_answer_block() -> None:
    fixes = tuple(question for question in QUESTIONS if question.fix is not None)
    sheet = render_sheet("Fix only", fixes, {})
    assert "file is read.\n\n## fix-it\n" in sheet
