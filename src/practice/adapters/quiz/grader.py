"""An answer sheet becomes a verdict. The choices in the domain, the code here.

Satisfies `practice.domain.ports.Grader` for `ExerciseKind.QUIZ` (Phase 25).
Three decisions:

* **The sheet comes from the attempt's log**, through `latest_source`, as it
  does for every file-based kind: a verdict is derived from something
  persisted, never from whatever is in the workspace at the moment.
* **A choice question is one check, graded in the domain** by
  `practice.domain.quiz.grade`. This module only puts the reports in order.
* **A fix question is graded by its suite, through the kata runner**, one
  check per test with ids `<question>/<test>`. The runner is the same object
  `KataGrader` holds -- injected by `build_graders` rather than built here --
  because it writes `solution.py` under a lock, and two runners are two
  locks over one kind of file (ADR 0029's reason, unchanged). The suite needs
  a `KataSpec` to say which tests and how long, so one is built per question:
  the runner reads `tests`, `time_limit_seconds` and `language` and nothing
  else, and a narrower protocol for those three would be a second runner
  interface with one implementation.

A fix question answered with nothing -- the heading deleted, the block
emptied -- is one failing check that says so, not a pytest run against an
empty module whose collection error reads as a broken suite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from practice.adapters.kata.grader import latest_source, reports_for
from practice.domain.exercise import KataSpec, QuizSpec
from practice.domain.quiz import grade, parse_sheet
from practice.domain.verdict import CheckReport, Severity, Verdict

if TYPE_CHECKING:
    from practice.adapters.kata.grader import KataRunner
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from practice.domain.ports import Workspace
    from practice.domain.quiz import Answer, Question

__all__ = ["QuizGrader", "QuizGraderError", "grade_sheet"]

#: The language a fix question is written in. Python is the only language the
#: kata runner speaks, so it is the only one a fix question can be in.
FIX_LANGUAGE: Final = "python"


class QuizGraderError(Exception):
    """Asked to grade something with no saved sheet, or something not a quiz.

    A programming error, as `ContainerGraderError` is: *you did not submit
    anything* is not a verdict a solver can act on.
    """


class QuizGrader:
    """Satisfies `practice.domain.ports.Grader` for `ExerciseKind.QUIZ`."""

    __slots__ = ("_runner",)

    def __init__(self, runner: KataRunner) -> None:
        self._runner = runner

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict:
        """Every question on the latest saved sheet, in the order asked."""
        spec = exercise.spec
        if not isinstance(spec, QuizSpec):
            raise QuizGraderError(
                f"{exercise.id} is a {exercise.kind.value}, which this grader "
                f"does not know how to read"
            )
        source = latest_source(attempt)
        if source is None:
            raise QuizGraderError(
                f"attempt {attempt.id.short} has saved no answers, so there is "
                f"nothing to grade"
            )
        return grade_sheet(spec, source, self._runner, workspace)


def grade_sheet(
    spec: QuizSpec, sheet: str, runner: KataRunner, workspace: Workspace
) -> Verdict:
    """The whole verdict for one sheet. Split out for the content suite.

    It is the function the grader calls, so a reference graded by the suite
    and a sheet graded on submission cannot be graded differently.
    """
    answers = parse_sheet(sheet, spec.questions)
    reports: list[CheckReport] = []
    for question in spec.questions:
        answer = answers.get(question.id)
        if question.fix is None:
            reports.append(grade(question, answer))
        else:
            reports.extend(_fix_reports(question, answer, runner, workspace))
    return Verdict(reports=tuple(reports))


def _fix_reports(
    question: Question, answer: Answer | None, runner: KataRunner, workspace: Workspace
) -> tuple[CheckReport, ...]:
    """One report per test, each id and label naming the question it is under."""
    assert question.fix is not None  # noqa: S101  (only fix questions come here)
    if answer is None or answer.problem is not None or not (answer.code or "").strip():
        return (
            CheckReport(
                check_id=f"{question.id}/answered",
                label=f"{question.label}: you wrote a fix",
                severity=Severity.REQUIRED,
                passed=False,
                explanation=(
                    answer.problem
                    if answer is not None and answer.problem is not None
                    else f"There is no code under `## {question.id}` in the sheet."
                ),
            ),
        )
    suite = KataSpec(
        language=FIX_LANGUAGE,
        stub=question.fix.tests,
        tests=question.fix.tests,
        reference=question.fix.tests,
        time_limit_seconds=question.fix.time_limit_seconds,
    )
    run = runner.run(workspace, suite, answer.code or "")
    if not run.ran:
        return (
            CheckReport(
                check_id=f"{question.id}/suite-ran",
                label=f"{question.label}: the hidden tests ran against your fix",
                severity=Severity.REQUIRED,
                passed=False,
                expected="the suite collects and runs its tests",
                actual=run.why_it_did_not_run(suite),
                explanation=run.output or None,
            ),
        )
    return tuple(
        CheckReport(
            check_id=f"{question.id}/{report.check_id}",
            label=f"{question.label}: {report.label}",
            severity=report.severity,
            passed=report.passed,
            expected=report.expected,
            actual=report.actual,
            explanation=report.explanation,
        )
        for report in reports_for(run, suite)
    )
