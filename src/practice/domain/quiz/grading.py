"""A choice, a line or an order becomes one check report. Pure, and total.

**What a failure says is the design**, more than whether it fails. A quiz
that answered *wrong* and nothing else would be a quiz you pass by
elimination; one that answered *wrong, the right one is C* would be one you
pass on the second submission without learning anything. So a failed
question shows **why the option you chose is wrong**, which is the sentence
the question was written to deliver, and never which option is right. A
failed submission is a logged try (ADR 0029), so the review grade still sees
how many it took, and the full set of explanations is the finished attempt's
to show (`partials/quiz-review.html`).

The one exception is deliberate: a select-all answer whose every choice is
right but which stops short is told so. Saying nothing would leave the solver
re-examining options that were fine, which is a wrong lesson rather than a
withheld one.

A fix question is not graded here. Its answer is code, its oracle is a test
suite that has to run in a process, and the domain starts none; the adapter
(`adapters/quiz/grader.py`) runs it through the kata runner.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING, Final

from practice.domain.errors import InvalidValueError
from practice.domain.quiz.questions import QuestionFormat
from practice.domain.verdict import CheckReport, Severity

if TYPE_CHECKING:
    from practice.domain.quiz.questions import Question
    from practice.domain.quiz.sheet import Answer

__all__ = ["grade"]

_LINE_NUMBER: Final = re.compile(r"0*([0-9]{1,9})")
#: How much of a refused line answer the verdict repeats.
_SHOWN: Final = 20


def grade(question: Question, answer: Answer | None) -> CheckReport:
    """One required check for one question, passed only on the exact answer."""
    if question.format is QuestionFormat.FIX:
        raise InvalidValueError(
            f"{question.id!r} is a fix question, which its test suite grades"
        )
    if answer is None or answer.is_blank:
        return _failed(question, "Not answered.")
    if answer.problem is not None:
        return _failed(question, answer.problem)
    if question.format is QuestionFormat.LINE:
        return _line(question, answer.values)
    if question.format is QuestionFormat.ORDER:
        if answer.values == question.answer:
            return _passed(question)
        return _failed(question, _order(question, answer.values))
    return _choice(question, answer.values)


def _choice(question: Question, chosen: tuple[str, ...]) -> CheckReport:
    """`single` and `multiple`, which differ only in how many may be chosen."""
    unknown = [value for value in chosen if question.option(value) is None]
    if unknown:
        return _failed(question, f"There is no option {_quoted(unknown)}.")
    repeated = sorted(value for value, count in Counter(chosen).items() if count > 1)
    if repeated:
        return _failed(question, f"{_quoted(repeated)} is chosen more than once.")
    if question.format is QuestionFormat.SINGLE and len(chosen) > 1:
        return _failed(
            question, f"This question takes one answer, and {len(chosen)} were given."
        )
    if set(chosen) == set(question.answer):
        return _passed(question)
    wrong = [value for value in chosen if value not in question.answer]
    if not wrong:
        return _failed(
            question,
            "Everything you chose is right, and there is more to choose.",
        )
    reasons = []
    for value in wrong:
        option = question.option(value)
        assert option is not None  # noqa: S101  (checked as unknown above)
        reasons.append(f"You chose `{value}`: {option.why.strip()}")
    return _failed(question, "\n\n".join(reasons))


def _line(question: Question, chosen: tuple[str, ...]) -> CheckReport:
    """By number rather than by text, so `08` is line 8 and not a wrong answer."""
    if len(chosen) != 1:
        return _failed(
            question,
            f"This question takes one line number, and {len(chosen)} were given.",
        )
    (value,) = chosen
    number = _line_number(value)
    if number is None or not 1 <= number <= question.line_count:
        # Cut, because the verdict keeps it: a five-thousand-digit answer is
        # refused now rather than raising, and was echoed whole.
        shown = value if len(value) <= _SHOWN else f"{value[:_SHOWN]}..."
        return _failed(
            question,
            f"`{shown}` is not a line of the snippet, which runs from 1 to "
            f"{question.line_count}.",
        )
    if number == int(question.answer[0]):
        return _passed(question)
    return _failed(question, f"Line {number} is not the one.")


def _line_number(value: str) -> int | None:
    """`08` as 8; `None` for anything `int` would refuse or should not be asked.

    Not `str.isdigit`, which is true of `²` and of a five-thousand-digit
    string, and `int` raises on both -- which made a typo in `answers.md` a
    traceback rather than a verdict. ASCII digits, and few enough of them to
    be a line number once the leading zeros are gone.
    """
    match = _LINE_NUMBER.fullmatch(value)
    return int(match.group(1)) if match else None


def _order(question: Question, chosen: tuple[str, ...]) -> str:
    """Why an order is wrong: not a permutation, or the first step out of place.

    The first misplaced position is said because it is what a solver would
    find by comparing anyway, and it localises the mistake without giving away
    where anything goes.
    """
    known = [option.id for option in question.options]
    unknown = [value for value in chosen if value not in known]
    if unknown:
        return f"There is no step {_quoted(unknown)}."
    missing = [value for value in known if value not in chosen]
    repeated = sorted(value for value, count in Counter(chosen).items() if count > 1)
    if missing or repeated:
        parts = []
        if missing:
            parts.append(f"{_quoted(missing)} is not placed")
        if repeated:
            parts.append(f"{_quoted(repeated)} is placed twice")
        return f"An order places every step exactly once: {'; '.join(parts)}."
    position = next(
        number
        for number, (given, wanted) in enumerate(
            zip(chosen, question.answer, strict=True), 1
        )
        if given != wanted
    )
    return f"Step {position} is the first one out of place."


def _passed(question: Question) -> CheckReport:
    """No explanation on a pass. The finished attempt shows every one of them."""
    return CheckReport(
        check_id=question.id,
        label=question.label,
        severity=Severity.REQUIRED,
        passed=True,
    )


def _failed(question: Question, why: str) -> CheckReport:
    """`expected` is left empty on purpose: it would be the answer."""
    return CheckReport(
        check_id=question.id,
        label=question.label,
        severity=Severity.REQUIRED,
        passed=False,
        explanation=why,
    )


def _quoted(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)
