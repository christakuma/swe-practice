"""The quiz engine: questions, the answer sheet, and grading a choice.

The fifth exercise kind (Phase 25), and the first whose answer is not an
artifact. What it grades, beside the other engines:

* `domain/checks/`: a **repository**, through `RepoQuery`.
* `domain/drills/`: a **database and a result set**, through `DrillQuery`.
* `domain/containers/`: a **container definition**, through `BuildQuery`.
* `domain/quiz/`: **a choice from a closed set**, against a key written with
  the question. No port, because there is nothing to query: the answer is
  the sheet and the key is the spec. A fix question's code is the exception,
  and the adapter runs it.

There is no assertion vocabulary here, and that is not an omission. The other
three need one because an author describes an end state in terms of what can
be asked of it; a quiz author writes the answer down.

* `questions.py`: the five formats and what makes one representable.
* `sheet.py`: `answers.md`, read and written.
* `grading.py`: one question, one check report.
* `presentation.py`: option order, and the plain-text statement.
"""

from practice.domain.quiz.grading import grade
from practice.domain.quiz.presentation import (
    answer_key_text,
    presented_options,
    statement_text,
)
from practice.domain.quiz.questions import (
    FixSuite,
    Option,
    Question,
    QuestionFormat,
    validate_identifier,
)
from practice.domain.quiz.sheet import SHEET_FILE, Answer, parse_sheet, render_sheet

__all__ = [
    "SHEET_FILE",
    "Answer",
    "FixSuite",
    "Option",
    "Question",
    "QuestionFormat",
    "answer_key_text",
    "grade",
    "parse_sheet",
    "presented_options",
    "render_sheet",
    "statement_text",
    "validate_identifier",
]
