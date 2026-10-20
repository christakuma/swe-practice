"""How a quiz is shown: the options in an order that gives nothing away.

Two surfaces, and they cannot be handled the same way.

* **The page shuffles per attempt.** An author who writes the right option
  first, or last, or longest, has written a pattern, and a solver who has
  done six of these will have learnt it without meaning to. The order is a
  hash of the attempt and the option rather than a draw, so a reload shows
  the same page and nothing has to be stored to make it so.
* **The plain-text statement cannot.** `practice start`, the tutor export
  and the MCP server print `Exercise.statement`, which has no attempt to seed
  from, so they show the authored order. That is why an `order` question has
  to be *authored* scrambled -- its authored order would otherwise be its
  answer -- and why the content suite checks that the right option of a
  single-choice question is not always in the same place.

An `order` question is also never shown in its answer's order on the page:
a shuffle that happened to land on it would be the one draw that is a gift,
so it is rotated by one.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from practice.domain.quiz.questions import QuestionFormat
from practice.domain.quiz.sheet import SHEET_FILE

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.quiz.questions import Option, Question

__all__ = ["answer_key_text", "presented_options", "statement_text"]


def presented_options(question: Question, seed: str) -> tuple[Option, ...]:
    """The options in this attempt's order. `seed` is the attempt id."""
    shuffled = tuple(
        sorted(question.options, key=lambda option: _rank(seed, question.id, option.id))
    )
    if (
        question.format is QuestionFormat.ORDER
        and tuple(option.id for option in shuffled) == question.answer
    ):
        return (*shuffled[1:], shuffled[0])
    return shuffled


def _rank(seed: str, question_id: str, option_id: str) -> str:
    digest = hashlib.sha256(f"{seed}\x00{question_id}\x00{option_id}".encode())
    return digest.hexdigest()


#: How each format is answered, as the sentence under it in the statement.
_HOW: dict[QuestionFormat, str] = {
    QuestionFormat.SINGLE: "one option id",
    QuestionFormat.MULTIPLE: "every option id that applies, separated by commas",
    QuestionFormat.LINE: "one line number",
    QuestionFormat.ORDER: "every option id, first to last, separated by commas",
}


def statement_text(questions: Sequence[Question]) -> str:
    """Every question as plain text, for the surfaces that are not a page.

    Everything the form shows and nothing it does not: the context, the
    prompt, the options with their ids, a snippet with its line numbers, and
    where in `answers.md` the answer goes. No `why`, and no answer.
    """
    total = len(questions)
    blocks = []
    for number, question in enumerate(questions, start=1):
        lines = [f"Question {number} of {total} ({question.id})"]
        if question.context is not None:
            lines.extend(["", question.context.strip()])
        lines.extend(["", question.prompt.strip()])
        if question.format is QuestionFormat.LINE:
            width = len(str(question.line_count))
            lines.append("")
            lines.extend(
                f"  {index:>{width}} | {text}".rstrip()
                for index, text in enumerate(question.lines, start=1)
            )
        if question.options:
            width = max(len(option.id) for option in question.options)
            lines.append("")
            lines.extend(
                f"  {option.id:<{width}}  {option.text.strip()}"
                for option in question.options
            )
        if question.format is QuestionFormat.FIX:
            lines.extend(
                [
                    "",
                    (
                        f"Answer with code, in the block under `## {question.id}` "
                        f"in {SHEET_FILE}."
                    ),
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    (
                        f"Answer on the line `{question.id}:` in {SHEET_FILE}, "
                        f"with {_HOW[question.format]}."
                    ),
                ]
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def answer_key_text(questions: Sequence[Question]) -> str:
    """Every answer and every explanation, for a quiz that is over.

    What `partials/quiz-review.html` draws under a finished quiz, as text, for
    the tutor export: ADR 0023's rule is that a tutor is shown what the solver
    has seen, and once the attempt is graded the solver has seen all of this.
    The explanations are kept exactly as written, because the tutor content
    suite looks for each one verbatim.
    """
    blocks = ["The answers"]
    for number, question in enumerate(questions, start=1):
        lines = [f"{number}. {question.label} ({question.id})"]
        if question.format is QuestionFormat.LINE:
            lines.append(f"Answer: line {question.answer[0]}")
        elif question.answer:
            lines.append(f"Answer: {', '.join(question.answer)}")
        for option in question.options:
            verdict = "right" if option.id in question.answer else "wrong"
            lines.append(f"- {option.id} ({verdict}): {option.text.strip()}")
            lines.append(f"  {option.why}")
        if question.explanation is not None:
            lines.append(question.explanation)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
