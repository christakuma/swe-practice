"""Running a kata's examples in its workspace: the "Run" button's adapter.

Satisfies `practice.domain.ports.ExampleRunner` (ADR 0029). One subprocess per
run, the harness in `examples_harness.py`, and the same pinning the hidden
suite gets from `pytest_runner`: `sys.executable`, `-I` so nothing on the
solver's machine changes what runs, `-X utf8` because `-I` drops
`PYTHONIOENCODING` along with the rest.

**It shares `PytestKataRunner`'s lock rather than having its own**, and that is
the one decision here with a failure attached. Both write `solution.py` into
the same directory and run it, so a Run pressed while a submission is grading
would otherwise swap the source out from under the hidden suite -- and a
verdict about code nobody submitted is the worst outcome this system has
(`pytest_runner`'s docstring). One lock, held by the one runner the composition
root builds, makes a run wait for a grading pass and the other way round.

**The report is truncated before every run**, which is `pytest_runner._install`'s
lesson applied unchanged: a run killed at the time limit writes nothing new, and
reading the previous run's file would report its results as this one's.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from practice.adapters.kata.examples_harness import (
    EXAMPLES_FILE,
    REPORT_FILE,
    SCHEMA_VERSION,
)
from practice.adapters.kata.grader import KataRunnerError
from practice.adapters.kata.pytest_runner import SOLUTION_MODULE
from practice.adapters.sandbox.execution import TIMEOUT_EXIT_CODE
from practice.domain.exercise import KataSpec
from practice.domain.trial import ExampleResult, Trial

if TYPE_CHECKING:
    from practice.adapters.kata.pytest_runner import PytestKataRunner
    from practice.domain.exercise import Exercise
    from practice.domain.ports import Workspace

__all__ = ["HARNESS_MODULE", "KataExampleRunner", "harness_source", "parse_trial"]

#: What the harness is called inside the workspace. A `practice_` prefix for
#: `PLUGIN_MODULE`'s reason: the workspace is on the solver's `sys.path`.
HARNESS_MODULE: Final = "practice_examples.py"

#: How much of the process's own output to carry when it said why it stopped.
_OUTPUT_TAIL: Final = 1500


class KataExampleRunner:
    """Runs a kata's examples against a source, in that kata's workspace."""

    __slots__ = ("_harness", "_runner")

    def __init__(self, runner: PytestKataRunner) -> None:
        self._runner = runner
        # Read once, at construction, for the reason the plugin is: a session
        # half an hour in should not depend on the package still being on disk.
        self._harness = harness_source()

    def run(self, exercise: Exercise, workspace: Workspace, source: str) -> Trial:
        spec = exercise.spec
        if not isinstance(spec, KataSpec):
            raise KataRunnerError(
                f"{exercise.id} is a {exercise.kind.value}, which has no examples "
                f"to run"
            )
        examples = json.dumps(
            [{"input": item.input, "output": item.output} for item in spec.examples]
        )

        with self._runner.lock:
            workspace.write_file(HARNESS_MODULE, self._harness)
            workspace.write_file(EXAMPLES_FILE, examples)
            workspace.write_file(REPORT_FILE, "")
            workspace.write_file(SOLUTION_MODULE, source)
            result = workspace.run_tool(
                [sys.executable, "-I", "-X", "utf8", HARNESS_MODULE],
                timeout=spec.time_limit_seconds,
            )
            document = _read(workspace)

        trial = parse_trial(document)
        if result.exit_code == TIMEOUT_EXIT_CODE:
            return Trial(
                examples=trial.examples,
                problem=(
                    f"stopped after {spec.time_limit_seconds}s: example "
                    f"{len(trial.examples) + 1} did not finish"
                ),
            )
        if document is None:
            # Exited without a report and without timing out: the interpreter
            # itself went down. Its own words are the only explanation there is.
            said = "\n".join(
                part for part in (result.stdout.strip(), result.stderr.strip()) if part
            )
            return Trial(
                problem=(
                    f"the examples did not run (exit {result.exit_code})"
                    + (f": {said[-_OUTPUT_TAIL:]}" if said else "")
                )
            )
        return trial


def harness_source() -> str:
    """The harness's own source, to be copied in. See `plugin_source`."""
    return (Path(__file__).parent / "examples_harness.py").read_text(encoding="utf-8")


def _read(workspace: Workspace) -> dict[str, Any] | None:
    """`None` for no readable report -- killed, half-written, or a stale shape."""
    try:
        document = json.loads(workspace.read_file(REPORT_FILE))
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict) or document.get("version") != SCHEMA_VERSION:
        return None
    return document


def parse_trial(document: dict[str, Any] | None) -> Trial:
    """The harness's JSON as a `Trial`, dropping what makes no sense.

    Tolerant in the way `parse_records` is: the writer is trusted code, so a
    malformed row is a bug in the harness and costs that row rather than the
    run. `None` is an empty trial with no problem; the caller decides what a
    missing report means, because only it knows how the process ended.
    """
    if document is None:
        return Trial()
    rows = document.get("examples")
    examples = tuple(
        ExampleResult(
            input=row["input"],
            expected=row["expected"],
            actual=_text(row.get("actual")),
            error=_text(row.get("error")),
            stdout=_text(row.get("stdout")) or "",
        )
        for row in (rows if isinstance(rows, list) else [])
        if isinstance(row, dict)
        and isinstance(row.get("input"), str)
        and isinstance(row.get("expected"), str)
    )
    return Trial(examples=examples, problem=_text(document.get("problem")))


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None
