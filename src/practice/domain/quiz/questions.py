"""What a quiz question is, and the five shapes an answer to one can take.

**Every format here has an answer that can be compared, and that is the rule
the whole kind rests on** (PLAN.md Phase 25). ADR 0003 refuses to grade free
text because nothing can say whether a sentence is right; a choice from a
closed set has its answer decided when the question was written, and grading
it is a set comparison. So the formats are what survives that rule, and
nothing is ever typed as prose:

* `single`: one option of several. Radio buttons.
* `multiple`: **the exact set**, not "any of". A partial credit scheme would
  make ticking every box a strategy, and the lesson in a select-all question
  is usually the option that looks right and is not.
* `line`: a numbered snippet, and the one line the question is about. One
  line rather than a set, because a question with two right lines is two
  questions, and a radio group does not tell the solver how many to pick.
* `order`: every option, first to last. The authored order is the order the
  options are *shown* in a plain-text statement, so it has to be scrambled;
  that is a rule about a good quiz rather than a representable one, and the
  content suite holds it (`tests/content/test_quizzes.py`).
* `fix`: code, graded by a hidden suite on what it does. The one format whose
  answer is an artifact, and the place the core bet comes back.

The invariants below are the **representability** half of the module
docstring's split in `domain/exercise.py`: a single-choice question with two
answers, or an answer naming an option that does not exist, can never be
passed, and that is a correctness hole rather than a quality one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from practice.domain.errors import InvalidValueError

if TYPE_CHECKING:
    # Only a type here: `exercise.py` imports this module to hold `QuizSpec`,
    # and builds and validates its counter-examples itself.
    from practice.domain.exercise import CounterExample

__all__ = [
    "FixSuite",
    "Option",
    "Question",
    "QuestionFormat",
    "validate_identifier",
]

_IDENTIFIER: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

#: The fewest options each choice format may offer. A single choice between two
#: is a true-or-false question, which is a legitimate one; a select-all over two
#: tells you most of the answer by being a select-all.
_FEWEST_OPTIONS: Final = {"single": 2, "multiple": 3, "order": 3}


class QuestionFormat(StrEnum):
    """Values match the `format:` key in `exercise.yaml`."""

    SINGLE = "single"
    MULTIPLE = "multiple"
    LINE = "line"
    ORDER = "order"
    FIX = "fix"

    @property
    def has_options(self) -> bool:
        return self in {
            QuestionFormat.SINGLE,
            QuestionFormat.MULTIPLE,
            QuestionFormat.ORDER,
        }


def validate_identifier(value: str, *, what: str) -> None:
    """Kebab-case, the shape every other id here has (PLAN.md §4.1).

    It matters more for a quiz than for a check: a question id is what a solver
    types at the start of a line in `answers.md`, and an option id is what they
    type after it, so both have to survive being written by hand.
    """
    if not _IDENTIFIER.match(value):
        raise InvalidValueError(f"{what} must be lowercase kebab-case, got {value!r}")


@dataclass(frozen=True, slots=True)
class Option:
    """One choice, and why it is right or wrong.

    **`why` is required on every option, including the right one**, because it
    is the half of a quiz that teaches. A wrong option is usually the tempting
    fix, and its explanation is the sentence that says when it breaks; a
    failed answer shows the solver the `why` of what they chose, and a pass
    shows them all of them.
    """

    id: str
    text: str
    why: str

    def __post_init__(self) -> None:
        validate_identifier(self.id, what="an option id")
        if not self.text.strip():
            raise InvalidValueError(f"option {self.id!r} has no text")
        if not self.why.strip():
            raise InvalidValueError(
                f"option {self.id!r} does not say why it is right or wrong"
            )


@dataclass(frozen=True, slots=True)
class FixSuite:
    """A fix question's hidden tests, and the wrong fixes they must catch.

    The tests run through the kata runner, against the code the solver wrote
    under the question's heading in `answers.md`, written out as
    `solution.py`. So the suite imports from `solution`, as a kata's does.

    **`counter_examples` are code files, each naming the tests it must fail**
    (ADR 0022), in the same `CounterExample` every declaratively graded kind
    uses. What differs is what the names refer to: a container's are check ids
    its spec declares, so `validate_checks` can refuse an unknown one, and a
    fix's are tests its suite reports only when it runs. Nothing here can
    check them, and `tests/content/test_quizzes.py` does, by running every file
    against the suite.
    """

    tests: str
    time_limit_seconds: int = 10
    counter_examples: tuple[CounterExample, ...] = ()

    def __post_init__(self) -> None:
        if not self.tests.strip():
            raise InvalidValueError("a fix question needs a tests file")
        if self.time_limit_seconds < 1:
            raise InvalidValueError("time_limit_seconds must be at least 1")

    @property
    def files(self) -> tuple[str, ...]:
        return (self.tests, *(example.file for example in self.counter_examples))


@dataclass(frozen=True, slots=True)
class Question:
    """One question: its context, what is asked, and the answer.

    **`context` is the evidence this question needs, in front of it.** A
    question that turns on a snippet, a number or a rule says so here rather
    than leaning on a ticket three screens up, which is the user's request
    for this kind in one sentence. Markdown, drawn as preformatted text, so an
    author's fences and alignment survive.

    `snippet` is a `line` question's numbered code. It is a field rather than
    a fence in `context` because the lines are what the solver picks from, so
    the page has to be able to number them and the grader has to know how many
    there are.

    `answer` is option ids for the three choice formats, one line number as a
    string for `line`, and empty for `fix`, whose answer is whatever its suite
    accepts. `explanation` is the lesson the question exists for, shown once
    the attempt is over; a `line` or `fix` question has no options to carry
    one, so it must say it here.
    """

    id: str
    format: QuestionFormat
    label: str
    prompt: str
    context: str | None = None
    options: tuple[Option, ...] = ()
    answer: tuple[str, ...] = ()
    snippet: str | None = None
    snippet_language: str = "text"
    explanation: str | None = None
    fix: FixSuite | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.id, what="a question id")
        if not self.label.strip():
            raise InvalidValueError(f"question {self.id!r} has no label")
        if not self.prompt.strip():
            raise InvalidValueError(f"question {self.id!r} has no prompt")
        for name, value in (
            ("context", self.context),
            ("explanation", self.explanation),
        ):
            if value is not None and not value.strip():
                raise InvalidValueError(
                    f"question {self.id!r} has a blank {name}; write it or leave it out"
                )
        if self.format.has_options:
            self._check_options()
        elif self.options:
            raise InvalidValueError(
                f"question {self.id!r} is a {self.format.value} question and "
                f"cannot offer options"
            )
        if self.format is QuestionFormat.LINE:
            self._check_line()
        elif self.snippet is not None:
            raise InvalidValueError(
                f"question {self.id!r} has a snippet, which only a line question "
                f"numbers; put other code in its context"
            )
        if self.format is QuestionFormat.FIX:
            self._check_fix()
        elif self.fix is not None:
            raise InvalidValueError(
                f"question {self.id!r} is a {self.format.value} question and "
                f"cannot carry a test suite"
            )

    def _check_options(self) -> None:
        fewest = _FEWEST_OPTIONS[self.format.value]
        if len(self.options) < fewest:
            raise InvalidValueError(
                f"a {self.format.value} question needs at least {fewest} options; "
                f"{self.id!r} has {len(self.options)}"
            )
        ids = [option.id for option in self.options]
        duplicates = sorted({name for name in ids if ids.count(name) > 1})
        if duplicates:
            raise InvalidValueError(
                f"question {self.id!r} repeats option id(s): {', '.join(duplicates)}"
            )
        unknown = sorted(set(self.answer) - set(ids))
        if unknown:
            raise InvalidValueError(
                f"question {self.id!r} answers with option(s) it does not offer: "
                f"{', '.join(unknown)}"
            )
        if len(set(self.answer)) != len(self.answer):
            raise InvalidValueError(f"question {self.id!r} names an answer twice")
        if self.format is QuestionFormat.SINGLE and len(self.answer) != 1:
            raise InvalidValueError(
                f"a single-choice question has exactly one answer; {self.id!r} "
                f"has {len(self.answer)}"
            )
        if self.format is QuestionFormat.MULTIPLE and not self.answer:
            raise InvalidValueError(
                f"a select-all question needs at least one right option; "
                f"{self.id!r} has none"
            )
        if self.format is QuestionFormat.ORDER and len(self.answer) != len(ids):
            raise InvalidValueError(
                f"an order question's answer places every option; {self.id!r} "
                f"places {len(self.answer)} of {len(ids)}"
            )

    def _check_line(self) -> None:
        if self.snippet is None or not self.snippet.strip():
            raise InvalidValueError(f"line question {self.id!r} needs a snippet")
        if self.explanation is None:
            raise InvalidValueError(
                f"line question {self.id!r} has no options to explain it, so it "
                f"needs an explanation"
            )
        if len(self.answer) != 1 or not self.answer[0].isdigit():
            raise InvalidValueError(
                f"line question {self.id!r} is answered by one line number"
            )
        number = int(self.answer[0])
        if not 1 <= number <= self.line_count:
            raise InvalidValueError(
                f"line question {self.id!r} answers line {number}, and its "
                f"snippet has {self.line_count}"
            )

    def _check_fix(self) -> None:
        if self.fix is None:
            raise InvalidValueError(f"fix question {self.id!r} needs a tests file")
        if self.answer:
            raise InvalidValueError(
                f"fix question {self.id!r} is answered by code its suite accepts, "
                f"not by a key"
            )
        if self.explanation is None:
            raise InvalidValueError(
                f"fix question {self.id!r} has no options to explain it, so it "
                f"needs an explanation"
            )

    @property
    def lines(self) -> tuple[str, ...]:
        """The snippet's lines, numbered from 1 by position. Empty off `line`."""
        return tuple(self.snippet.splitlines()) if self.snippet is not None else ()

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def option(self, option_id: str) -> Option | None:
        """The option with this id, or `None` -- a solver can type anything."""
        for candidate in self.options:
            if candidate.id == option_id:
                return candidate
        return None
