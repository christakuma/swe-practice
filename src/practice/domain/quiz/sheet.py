"""`answers.md`: the one file a quiz is answered in, read and written here.

**The sheet is the attempt's editable source**, which is the decision that
kept a fifth kind one clause in `editable_source` (Phase 25). The web form
writes it, a solver at a terminal edits it by hand and submits it with
`practice submit --source`, and the tutor export and the MCP server show it
the way they show a kata's `solution.py`, with no branch for a quiz anywhere
along that path.

**Markdown, not YAML, and read by hand rather than by a library.** The reason
for Markdown is the fix question: its answer is code, and a fenced block under
a heading is how anyone already writes code inside prose, where a YAML block
scalar would make a solver indent Python by two more spaces and keep it there.
The reason for no library is where this lives. Whether a choice was right is
the whole verdict, so it belongs in the domain and under the coverage gate,
and the domain imports no third-party parser. The grammar is small enough to
own:

* A line `<question-id>: <answer>` outside a code block answers a choice,
  line or order question. Several values are separated by commas.
* A `## <question-id>` heading starts a fix question's answer, and the first
  fenced block after it is the code. Fences follow CommonMark: three or more
  backticks or tildes, closed by a run of the same character at least as
  long, and an unclosed fence runs to the end of the file.
* **Everything else is ignored**, so the instructions at the top, a note to
  self or a pasted stack trace cannot be misread as an answer. That is why the
  parser is told which ids are questions: `Note: ...` is prose, not an answer
  to a question called `note`.

A sheet cannot fail to parse. What can go wrong is per question -- unanswered,
answered twice, a heading with no code under it -- and each becomes that
question's failing check with a sentence in it, rather than one parse error
that hides which answers were fine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.domain.quiz.questions import QuestionFormat

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.quiz.questions import Question

__all__ = ["SHEET_FILE", "Answer", "parse_sheet", "render_sheet"]

#: What the workspace calls the sheet, and what `QuizSpec` requires its stub to
#: be named. One name, because the instructions a solver reads say it.
SHEET_FILE: Final = "answers.md"

_ANSWER_LINE: Final = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)\s*:(.*)$", re.IGNORECASE)
_HEADING: Final = re.compile(r"^##\s+(\S+)\s*$")
_FENCE: Final = re.compile(r"^(`{3,}|~{3,})")

#: The paragraph at the top of every sheet. Rendered rather than authored, so
#: every quiz explains its own file the same way.
_INSTRUCTIONS: Final = """\
Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read."""


@dataclass(frozen=True, slots=True)
class Answer:
    """What the sheet says for one question.

    `values` for a choice, line or order question, in the order written and
    lowercased, because an id is lowercase and a solver's caps lock is not a
    wrong answer. `code` for a fix question. `problem` when the sheet says
    something about this question that cannot be graded as an answer, written
    as the sentence the verdict will show.
    """

    values: tuple[str, ...] = ()
    code: str | None = None
    problem: str | None = None

    @property
    def is_blank(self) -> bool:
        return not self.values and not (self.code or "").strip() and not self.problem


def parse_sheet(text: str, questions: Sequence[Question]) -> dict[str, Answer]:
    """Every answer the sheet gives, by question id. An unanswered one is absent."""
    keyed = {
        question.id
        for question in questions
        if question.format is not QuestionFormat.FIX
    }
    fixes = {
        question.id for question in questions if question.format is QuestionFormat.FIX
    }
    answers: dict[str, Answer] = {}
    headed: set[str] = set()
    heading: str | None = None
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        fence = _FENCE.match(line)
        if fence:
            body, index = _fenced(lines, index, fence.group(1))
            if heading is not None and heading not in answers:
                answers[heading] = Answer(code=body)
            heading = None
            continue
        index += 1
        if match := _HEADING.match(line):
            # Case-blind like an answer line, so `## Q3` and `Q1: b` on one
            # sheet are both read, or neither -- never one of the two.
            named = match.group(1).lower()
            heading = named if named in fixes else None
            if heading is not None:
                headed.add(heading)
            continue
        match = _ANSWER_LINE.match(line)
        if match is None or match.group(1).lower() not in keyed:
            continue
        question_id = match.group(1).lower()
        if question_id in answers:
            answers[question_id] = Answer(
                problem=f"`{question_id}` is answered on two lines, so neither is read."
            )
            continue
        values = tuple(
            value.strip().lower()
            for value in match.group(2).split(",")
            if value.strip()
        )
        answers[question_id] = Answer(values=values)
    for question_id in sorted(headed - set(answers)):
        answers[question_id] = Answer(
            problem=f"There is no code block under `## {question_id}`."
        )
    return answers


def _fenced(lines: Sequence[str], start: int, opener: str) -> tuple[str, int]:
    """The body of the fence opening at `start`, and the index after it closes."""
    marker = opener[0]
    closer = re.compile(rf"^{re.escape(marker)}{{{len(opener)},}}\s*$")
    body: list[str] = []
    index = start + 1
    while index < len(lines):
        if closer.match(lines[index]):
            return "\n".join(body), index + 1
        body.append(lines[index])
        index += 1
    return "\n".join(body), index


def render_sheet(
    title: str, questions: Sequence[Question], answers: Mapping[str, Answer]
) -> str:
    """The sheet `parse_sheet` reads back as `answers`, in its one canonical form.

    Canonical because the content suite holds every authored stub and
    reference to it (`render_sheet(parse_sheet(stub)) == stub`), so a sheet
    a solver is handed and one the web form writes cannot differ in a way
    that only one of them parses.

    A problem is not rendered: it is the parser's account of a sheet, not
    something a sheet says, and the form that renders a sheet never has one.
    """
    sections = [f"# {title}: your answers", _INSTRUCTIONS]
    keyed = [
        f"{question.id}: {', '.join(answer.values)}".rstrip()
        for question in questions
        if question.format is not QuestionFormat.FIX
        for answer in (answers.get(question.id, Answer()),)
    ]
    if keyed:
        sections.append("\n".join(keyed))
    for question in questions:
        if question.format is QuestionFormat.FIX:
            code = (answers.get(question.id, Answer()).code or "").rstrip("\n")
            fence = "`" * max(3, _longest_backtick_run(code) + 1)
            sections.append(f"## {question.id}\n\n{fence}python\n{code}\n{fence}")
    return "\n\n".join(sections) + "\n"


def _longest_backtick_run(code: str) -> int:
    """The longest backtick fence the code itself opens, so ours can be longer."""
    runs = [
        len(match.group(1))
        for line in code.splitlines()
        if (match := re.match(r"^(`+)", line))
    ]
    return max(runs, default=0)
