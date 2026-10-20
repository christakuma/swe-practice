"""A quiz on a page: the form it is drawn as, and the sheet a post becomes.

**The form is a view of `answers.md`, never a second source of truth.** A post
is rendered into a sheet by the domain's `render_sheet` and submitted like any
other editable source, and the page is drawn by parsing the latest sheet back
(Phase 25). So an attempt answered half in the browser and half in an editor
at a terminal is one attempt with one history, and what the grader read is
always something the log holds.

**One field name per question, and the format decides how many values it
carries.** A radio group sends one value, a set of checkboxes sends several,
and an `order` question is drawn as one `<select>` per step under the same
name, so the browser sends the steps in order. All four arrive as a list
under `q:<id>`, which is the shape `Answer.values` already is -- and an order
with a step chosen twice reaches the grader as exactly that, to be told so.

**The sheet seeds the form, not the workspace file.** `OpenWorkbench` reads
the editable file from the workspace, which for a kata is the working copy.
A quiz answered in the browser never writes its workspace file, so a reload
after a failed submission would draw the blank stub again; the log has what
was submitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from practice.domain.attempt import SolutionSaved
from practice.domain.quiz import (
    Answer,
    QuestionFormat,
    parse_sheet,
    presented_options,
    render_sheet,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.attempt import Attempt
    from practice.domain.exercise import QuizSpec
    from practice.domain.quiz import Option, Question

__all__ = [
    "FORMAT_NAMES",
    "QuizItem",
    "field_name",
    "latest_sheet",
    "quiz_items",
    "sheet_from_form",
]

#: What each format asks the solver to do, as the page says it above the
#: question. Said rather than left to the controls, because a set of checkboxes
#: and a radio group look alike until one is clicked.
FORMAT_NAMES: Final[Mapping[str, str]] = MappingProxyType(
    {
        QuestionFormat.SINGLE.value: "choose one",
        QuestionFormat.MULTIPLE.value: "choose every one that applies",
        QuestionFormat.LINE.value: "pick the line",
        QuestionFormat.ORDER.value: "put the steps in order",
        QuestionFormat.FIX.value: "fix the code",
    }
)


def field_name(question: Question) -> str:
    """The form field a question's answer arrives under."""
    prefix = "fix" if question.format is QuestionFormat.FIX else "q"
    return f"{prefix}:{question.id}"


@dataclass(frozen=True, slots=True)
class QuizItem:
    """One question as the page draws it: options in this attempt's order."""

    number: int
    question: Question
    options: tuple[Option, ...]
    answer: Answer

    @property
    def field(self) -> str:
        return field_name(self.question)

    @property
    def chosen(self) -> tuple[str, ...]:
        return self.answer.values

    @property
    def code(self) -> str:
        return self.answer.code or ""

    @property
    def right(self) -> tuple[Option, ...]:
        """The right options, in the answer's order. For the finished review."""
        found = (self.question.option(option_id) for option_id in self.question.answer)
        return tuple(option for option in found if option is not None)


def latest_sheet(attempt: Attempt, fallback: str | None) -> str:
    """The last sheet the attempt saved, or the workspace's copy before any."""
    saved = [event for event in attempt.events if isinstance(event, SolutionSaved)]
    return saved[-1].source if saved else (fallback or "")


def quiz_items(spec: QuizSpec, *, seed: str, sheet: str) -> tuple[QuizItem, ...]:
    """Every question, with the sheet's answer to it, in the order asked."""
    answers = parse_sheet(sheet, spec.questions)
    return tuple(
        QuizItem(
            number=number,
            question=question,
            options=presented_options(question, seed),
            answer=answers.get(question.id, Answer()),
        )
        for number, question in enumerate(spec.questions, start=1)
    )


def sheet_from_form(
    title: str, spec: QuizSpec, form: Mapping[str, Sequence[str]]
) -> str:
    """The sheet a posted form says, in `render_sheet`'s canonical form.

    `form` maps a field name to every value sent under it, in the order sent.
    Empty values are dropped, which is what an order step left on its
    placeholder sends.
    """
    answers: dict[str, Answer] = {}
    for question in spec.questions:
        values = [value for value in form.get(field_name(question), ()) if value]
        if question.format is QuestionFormat.FIX:
            code = values[0].replace("\r\n", "\n") if values else ""
            answers[question.id] = Answer(code=code)
        else:
            answers[question.id] = Answer(values=tuple(values))
    return render_sheet(title, spec.questions, answers)
