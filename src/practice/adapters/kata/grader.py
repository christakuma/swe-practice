"""Test results become check reports, and check reports become a verdict.

Satisfies `practice.domain.ports.Grader` structurally, like every adapter here
(ADR 0002). Three decisions in it are worth more than the code:

**One test, one check.** A kata's hidden suite is already a list of named
assertions about a solution, so mapping each to a `CheckReport` gives the same
feedback shape as a git scenario for free — the verdict panel, the review grade
and the progress tracking do not have to learn that katas are different. The
test's docstring is the label, so what a solver reads is the author's sentence
about what the solution must do rather than a function name (PLAN.md §7).

**A suite that did not run is one failing check, not nine.** A collection error
or a timeout produces no records at all, and reporting that as "every test
failed" would tell a solver their logic is wrong when the truth is that their
file does not import. `Verdict` refuses to be built empty for exactly this
reason — an empty verdict would have to be called a pass or a fail and both
answers are wrong — so the engine has to say something, and what it says is
`suite-ran: false` with the captured output attached.

**The complexity claim is surfaced, never graded.** Static Big-O analysis of
arbitrary code is not something to pretend to do, so the claim becomes an
*advisory* check: agreeing is a clean `PASS`, disagreeing or declining to
declare is `PASS_WITH_ADVISORIES` with both values side by side. That is the
`Severity.ADVISORY` mechanism doing the job §4.4 describes — you achieved the
goal, and here is the thing to reconcile — rather than a grader guessing at
asymptotics.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final, Protocol

from practice.domain.attempt import SolutionSaved
from practice.domain.exercise import KataSpec
from practice.domain.verdict import CheckReport, Severity, Verdict

if TYPE_CHECKING:
    from practice.adapters.kata.pytest_runner import KataRun, TestRecord
    from practice.domain.attempt import Attempt, ComplexityClaim
    from practice.domain.exercise import ComplexityExpectation, Exercise
    from practice.domain.ports import Workspace

__all__ = [
    "COMPLEXITY_CHECK_ID",
    "SUITE_CHECK_ID",
    "KataGrader",
    "KataRunner",
    "KataRunnerError",
    "check_id_for",
    "complexity_report",
    "label_for",
    "latest_source",
    "reports_for",
]

#: The synthesised check that stands in for a suite that never ran.
SUITE_CHECK_ID: Final = "suite-ran"

#: The advisory check carrying the complexity comparison.
COMPLEXITY_CHECK_ID: Final = "declared-complexity"

#: Anything that is not a letter, a digit or a hyphen, for deriving a check id.
_NOT_SLUG: Final = re.compile(r"[^a-z0-9]+")


class KataRunnerError(Exception):
    """The grader was asked to grade something it has no source for.

    A programming error rather than a solver mistake — a use case that graded
    before saving a solution — so it is an exception and not a failing check.
    Making it a check would put "you did not submit anything" in a verdict that
    the solver has no way to act on.
    """


class KataRunner(Protocol):
    """What this grader needs from a test runner.

    A protocol rather than the concrete `PytestKataRunner` so the mapping can be
    unit-tested in milliseconds against canned records, with no subprocess and
    no workspace. It earns its keep under the §13 rule on day one: two
    implementations, one of them the test stub that makes every case below
    cheap to cover — including the timeout, which is otherwise a ten-second
    test.
    """

    def run(self, workspace: Workspace, spec: KataSpec, source: str) -> KataRun: ...


class KataGrader:
    """Satisfies `practice.domain.ports.Grader` for `ExerciseKind.KATA`."""

    __slots__ = ("_runner",)

    def __init__(self, runner: KataRunner) -> None:
        self._runner = runner

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict:
        """Run the suite against the attempt's latest saved source.

        The source comes from the attempt's event log rather than from an
        argument, which is why `Grader.grade` takes an `Attempt` at all: the log
        is the record of what was submitted, so a verdict is always derived from
        something that is persisted and replayable. A grader handed a source
        directly could produce a verdict for code no attempt remembers.
        """
        spec = exercise.spec
        if not isinstance(spec, KataSpec):
            raise KataRunnerError(
                f"{exercise.id} is a {exercise.kind.value}, which this grader "
                f"does not know how to run"
            )

        source = latest_source(attempt)
        if source is None:
            raise KataRunnerError(
                f"attempt {attempt.id.short} has saved no solution, so there is "
                f"nothing to grade"
            )

        run = self._runner.run(workspace, spec, source)
        reports = (
            reports_for(run, spec) if run.ran else (_suite_did_not_run(run, spec),)
        )
        complexity = complexity_report(spec.complexity, attempt.declared_complexity)
        return Verdict(reports=(*reports, *([complexity] if complexity else ())))


def latest_source(attempt: Attempt) -> str | None:
    """The most recent source the attempt saved, or `None` if it saved none.

    The *last* one, not the first: a solver saves repeatedly while working and
    what is graded is what they finished with. The earlier snapshots stay in the
    log, which is what makes "where did I go wrong" possible later.
    """
    saved = [event for event in attempt.events if isinstance(event, SolutionSaved)]
    return saved[-1].source if saved else None


def reports_for(run: KataRun, spec: KataSpec) -> tuple[CheckReport, ...]:
    """One report per test, in the order the suite declared them.

    Ids are derived from the node id and deduplicated, because `Verdict` refuses
    duplicates and a parametrized suite can produce two tests whose names differ
    only in characters an id cannot hold.
    """
    del spec  # part of the signature so a future per-kind rule has somewhere to go
    reports = []
    used: set[str] = set()
    for record in run.tests:
        check_id = _unique(check_id_for(record), used)
        reports.append(
            CheckReport(
                check_id=check_id,
                label=label_for(record),
                severity=Severity.REQUIRED,
                passed=record.passed,
                expected="the test passes",
                actual=_actual(record),
                explanation=record.message if not record.passed else None,
            )
        )
    return tuple(reports)


def check_id_for(record: TestRecord) -> str:
    """`test_handles_repeated_values` becomes `handles-repeated-values`.

    Kebab-case because that is the shape every other id in the system has
    (PLAN.md §4.1), and without the `test_` prefix because every one of them
    would carry it and an id that is the same on every check is not an id.
    """
    stem = record.name.removeprefix("test_").lower()
    slug = _NOT_SLUG.sub("-", stem).strip("-")
    return slug or "test"


def label_for(record: TestRecord) -> str:
    """The docstring's first line, or the test name made readable.

    The fallback is not cosmetic. A kata whose author wrote no docstrings still
    has to produce a verdict a human can read, and `handles repeated values` is
    a great deal closer to a sentence than `test_handles_repeated_values`.

    A docstring that is only whitespace falls back too, rather than indexing
    into an empty list of lines — which is what it did until a test asked.
    """
    lines = (record.doc or "").strip().splitlines()
    if lines and lines[0].strip():
        return lines[0].strip()
    return record.name.removeprefix("test_").replace("_", " ")


def complexity_report(
    expectation: ComplexityExpectation | None, claim: ComplexityClaim | None
) -> CheckReport | None:
    """The advisory comparison, or `None` when there is nothing to compare.

    No expectation means the author did not state one, and inventing a check
    against nothing would fail every attempt at an exercise whose content is
    simply quieter than the others.
    """
    if expectation is None:
        return None

    expected = f"time {expectation.expected_time}, space {expectation.expected_space}"
    if claim is None:
        return CheckReport(
            check_id=COMPLEXITY_CHECK_ID,
            label="You declared the cost of your solution.",
            severity=Severity.ADVISORY,
            passed=False,
            expected=expected,
            actual="not declared",
            explanation=(
                "Naming the time and space cost before submitting is the habit "
                "this exercise is for; the tool never infers it from your code."
            ),
        )

    return CheckReport(
        check_id=COMPLEXITY_CHECK_ID,
        label="Your declared cost matches what this exercise expects.",
        severity=Severity.ADVISORY,
        passed=claim.agrees_with(expectation),
        expected=expected,
        actual=f"time {claim.time}, space {claim.space}",
        explanation=(
            "Never auto-graded: static Big-O analysis of arbitrary code is not "
            "something this tool pretends to do. Both values are shown so you "
            "can reconcile them -- one of the two is wrong, and working out "
            "which is the exercise."
        ),
    )


def _suite_did_not_run(run: KataRun, spec: KataSpec) -> CheckReport:
    """The one report that stands in for a suite that produced no results."""
    return CheckReport(
        check_id=SUITE_CHECK_ID,
        label=f"The hidden test suite ran against your {spec.language} solution.",
        severity=Severity.REQUIRED,
        passed=False,
        expected="the suite collects and runs its tests",
        actual=run.why_it_did_not_run(spec),
        explanation=run.output or None,
    )


def _actual(record: TestRecord) -> str:
    """What happened, with the line it happened on when there is one."""
    if record.passed:
        return "passed"
    where = f" at {record.location}" if record.location else ""
    return f"{record.outcome.value}{where}"


def _unique(check_id: str, used: set[str]) -> str:
    """Append a counter rather than dropping a collision.

    A dropped report is a test whose result silently did not reach the verdict,
    which is the worst available outcome: the attempt would pass with a check
    nobody evaluated.
    """
    candidate = check_id
    counter = 2
    while candidate in used:
        candidate = f"{check_id}-{counter}"
        counter += 1
    used.add(candidate)
    return candidate
