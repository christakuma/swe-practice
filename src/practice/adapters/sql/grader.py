"""A drill answer becomes a verdict. `ScenarioGrader`'s counterpart.

Satisfies `practice.domain.ports.Grader` for `ExerciseKind.SQL_DRILL`,
structurally like every adapter here (ADR 0002). Three decisions in it are worth
more than the code, and the first two are both about the same thing: a drill has
one failure mode the other two kinds do not.

**`answer-ran` is a synthesised required check, and it comes first.** An answer
with a syntax error produces no result set and no table changes, so every
declared check fails — and a verdict reading *ten failures* for one misplaced
keyword tells a solver their SQL is wrong in ten ways when it is wrong in one.
This is the same move `KataGrader` makes with `suite-ran` for a suite that did
not collect, and for the same reason: `Verdict` refuses to be built empty, so
the engine has to say *something*, and what it says should be the one true
thing. The difference is that the drill's declared checks still run and are
still reported — they are real information about a database the answer partly
changed — so the check is additive rather than a replacement.

**The database is interrogated through the same `DrillQuery` the assertions
read, and it is closed before the verdict leaves.** The connection is an
in-memory database that exists only for this pass, which is the property
`engine.py` argues makes re-grading idempotent; a grader that let it escape
would have made that property depend on a caller remembering.

**The answer comes from the attempt's event log, not from an argument.** The
same rule `KataGrader` states: a verdict is always derived from something
persisted and replayable, so a grader handed source directly could produce a
verdict for an answer no attempt remembers.
"""

from __future__ import annotations

from contextlib import closing
from typing import TYPE_CHECKING, Final

from practice.adapters.kata.grader import latest_source
from practice.adapters.sql.engine import run_answer
from practice.domain.drills import registry as drills
from practice.domain.exercise import SqlDrillSpec
from practice.domain.verdict import CheckReport, Severity, Verdict

if TYPE_CHECKING:
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from practice.domain.ports import DrillQuery, Workspace

__all__ = ["ANSWER_CHECK_ID", "SqlDrillGrader", "SqlDrillGraderError", "answer_report"]

#: The synthesised check that stands in for an answer SQLite would not run.
ANSWER_CHECK_ID: Final = "answer-ran"


class SqlDrillGraderError(Exception):
    """The grader was asked to grade something it has no answer for.

    A programming error rather than a solver mistake — a use case that graded
    before saving — so it is an exception and not a failing check. The same line
    `KataRunnerError` draws, for the same reason: "you did not submit anything"
    in a verdict is something the solver cannot act on.
    """


class SqlDrillGrader:
    """Satisfies `practice.domain.ports.Grader` for `ExerciseKind.SQL_DRILL`."""

    __slots__ = ()

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict:
        """Seed a database, run the saved answer, and evaluate every check.

        The seed is read out of the workspace rather than out of the content
        directory, which is the same choice `_install_fixture` makes about a
        fixture and for the same reason: what grades is what was provisioned, so
        an exercise edited mid-attempt cannot change the rules underneath a
        solver.
        """
        spec = exercise.spec
        if not isinstance(spec, SqlDrillSpec):
            raise SqlDrillGraderError(
                f"{exercise.id} is a {exercise.kind.value}, which this grader "
                f"does not know how to run"
            )

        answer = latest_source(attempt)
        if answer is None:
            raise SqlDrillGraderError(
                f"attempt {attempt.id.short} has saved no answer, so there is "
                f"nothing to grade"
            )

        seed = workspace.read_file(spec.seed)
        with closing(
            run_answer(
                seed=seed,
                answer=answer,
                timeout_seconds=spec.statement_timeout_seconds,
            )
        ) as query:
            return Verdict(
                reports=(
                    answer_report(query),
                    *(drills.evaluate(check, query) for check in spec.checks),
                )
            )


def answer_report(query: DrillQuery) -> CheckReport:
    """The synthesised `answer-ran` check: did SQLite accept the answer at all.

    Always present and always required, including on a pass. A check that only
    appeared on failure would make the verdict panel's shape depend on the
    outcome, and the one thing a solver reads first should be in the same place
    every time.

    The error message is SQLite's own, in `actual`, because it is the single
    most useful sentence available — `near "FORM": syntax error` ends the problem
    where a traceback would start one.
    """
    error = query.error()
    return CheckReport(
        check_id=ANSWER_CHECK_ID,
        label="SQLite ran your answer.",
        severity=Severity.REQUIRED,
        passed=error is None,
        expected="every statement runs",
        actual="it ran" if error is None else error,
        explanation=(
            None
            if error is None
            else (
                "The checks below ran anyway, against the database as your "
                "answer left it -- statements before the failing one still took "
                "effect."
            )
        ),
    )
