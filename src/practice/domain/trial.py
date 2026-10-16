"""What running a kata's examples against a solver's source produced.

**A trial is the "Run" button, and the thing worth saying is what it is not:
a verdict** (ADR 0029). LeetCode and NeetCode both separate *run* from
*submit*, and the separation is the point of having two buttons. Running the
code against the examples on the page -- the ones the solver can already read
-- answers "does this do what I think it does?" Submitting it against the
hidden suite answers "is it right?" A run that graded the hidden suite would
make the second button a formality and turn the suite into something to
iterate against rather than something that checks.

So a trial carries no `CheckReport`s and cannot become a `Verdict`: it is the
examples, each with the value the solver's code gave and the value the page
says it should give. Nothing about it is persisted, because an attempt's log
is a record of what the solver *did in the exercise* (Phase 8, §16), and a
run is closer to a keystroke than to an answer.

**Values are carried as `repr` strings**, the form ADR 0027 compares examples
in: `==` would accept `1` for `True` and a list for a tuple, and each of those
is a difference a solver reading the output would be misled by. The strings
are made in the solver's process, which is the only place their values exist.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ExampleResult", "Trial"]


@dataclass(frozen=True, slots=True)
class ExampleResult:
    """One example: what it ran, what came back, and what should have.

    `actual` is `None` when the example raised rather than returning, and
    `error` then holds the exception's last line -- the line a solver reads
    first in a traceback, and the only one that is about their code rather
    than the harness's.
    """

    input: str
    expected: str
    actual: str | None = None
    error: str | None = None
    stdout: str = ""

    @property
    def passed(self) -> bool:
        return self.error is None and self.actual == self.expected


@dataclass(frozen=True, slots=True)
class Trial:
    """Every example, in the order the kata declares them.

    `problem` is set when the examples could not be run at all -- a source
    that does not import, a run that hit the time limit -- and `examples` is
    then empty. The same distinction `KataRun.ran` keeps for the hidden suite,
    and for the same reason: *nothing ran* is a different thing from
    *everything failed*, and a page that drew it as a row of red would send a
    solver looking for a logic error in a file with a syntax error.
    """

    examples: tuple[ExampleResult, ...] = ()
    problem: str | None = None

    @property
    def ran(self) -> bool:
        return self.problem is None

    @property
    def passed(self) -> int:
        return sum(1 for example in self.examples if example.passed)

    @property
    def all_passed(self) -> bool:
        return self.ran and self.passed == len(self.examples)
