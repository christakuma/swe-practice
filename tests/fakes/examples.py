"""A stand-in for the Run button's runner: a canned trial, and a record of the asks.

The second implementation `ExampleRunner` needs under §13, beside
`KataExampleRunner`. It returns whatever trial it was built with rather than
evaluating anything, because what the web and application tests assert is the
*route* -- which attempt, which source, which fragment came back -- and the
evaluation is the real harness's to be tested against real Python
(`tests/integration/kata/test_examples.py`).

It records the workspace's `disposed` flag as well as the source, for the
reason `RecordingGrader` does: a run into a workspace that has been disposed of
is the ordering bug a use case can have, and the flag is only true *during*
the call if the bug is there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.trial import ExampleResult, Trial

if TYPE_CHECKING:
    from practice.domain.exercise import Exercise
    from practice.domain.ports import Workspace

__all__ = ["RecordingExampleRunner", "a_trial"]


def a_trial(*, passing: int = 2, failing: int = 0) -> Trial:
    """A trial with this many examples matching and this many not."""
    good = tuple(
        ExampleResult(input=f"f({n})", expected=str(n), actual=str(n))
        for n in range(passing)
    )
    bad = tuple(
        ExampleResult(input=f"g({n})", expected=str(n), actual="None")
        for n in range(failing)
    )
    return Trial(examples=good + bad)


class RecordingExampleRunner:
    """Satisfies `ExampleRunner`. Returns `trial`, remembers what it was handed."""

    def __init__(self, trial: Trial | None = None) -> None:
        self.trial = trial if trial is not None else a_trial()
        self.calls: list[tuple[str, str, bool]] = []

    def run(self, exercise: Exercise, workspace: Workspace, source: str) -> Trial:
        self.calls.append(
            (str(exercise.id), source, getattr(workspace, "disposed", False))
        )
        return self.trial
