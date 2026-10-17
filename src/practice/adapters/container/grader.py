"""A container definition becomes a verdict. `SqlDrillGrader`'s counterpart.

Satisfies `practice.domain.ports.Grader` for `ExerciseKind.CONTAINER`, and makes
the same three decisions the drill grader does, for the same reasons:

* **`definition-parsed` is a synthesised required check, and it comes first.**
  A Dockerfile with an unknown instruction produces no stages, so every
  declared check fails, and *eight failures* for one typo tells the solver they
  are wrong in eight ways. The declared checks still run and are still
  reported, against whatever could be read.
* **The editable file comes from the attempt's log**, through `latest_source`,
  and the rest of the build context from the workspace. A verdict is derived
  from something persisted, and the context is what was provisioned, so an
  exercise edited mid-attempt cannot change the rules underneath a solver.
* **No daemon, ever** (ADR 0030). Nothing here builds or runs an image, which
  is why this module needs neither `subprocess` nor the sandbox's command
  policy: it reads files and parses them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from practice.adapters.container.build_query import ParsedBuildQuery, context_files
from practice.adapters.kata.grader import latest_source
from practice.domain.containers import registry as containers
from practice.domain.exercise import ContainerSpec
from practice.domain.verdict import CheckReport, Severity, Verdict

if TYPE_CHECKING:
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from practice.domain.ports import BuildQuery, Workspace

__all__ = [
    "DEFINITION_CHECK_ID",
    "ContainerGrader",
    "ContainerGraderError",
    "definition_report",
]

#: The synthesised check that stands in for a definition Docker would not read.
DEFINITION_CHECK_ID: Final = "definition-parsed"


class ContainerGraderError(Exception):
    """Asked to grade something with no saved answer. A programming error, as
    `SqlDrillGraderError` is: *you did not submit anything* is not a verdict a
    solver can act on.
    """


class ContainerGrader:
    """Satisfies `practice.domain.ports.Grader` for `ExerciseKind.CONTAINER`."""

    __slots__ = ()

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict:
        """Read the context, overlay the saved answer, and evaluate every check."""
        spec = exercise.spec
        if not isinstance(spec, ContainerSpec):
            raise ContainerGraderError(
                f"{exercise.id} is a {exercise.kind.value}, which this grader "
                f"does not know how to read"
            )
        source = latest_source(attempt)
        if source is None:
            raise ContainerGraderError(
                f"attempt {attempt.id.short} has saved no answer, so there is "
                f"nothing to grade"
            )
        # The stub sits at the root of the build context, so its directory is it.
        root = workspace.resolve(spec.stub).parent
        query = ParsedBuildQuery(
            context=context_files(root), editable=spec.stub, source=source
        )
        return grade_query(spec, query)


def grade_query(spec: ContainerSpec, query: BuildQuery) -> Verdict:
    """Every check over an already-built query, with the synthesised one first.

    Split out so the content suite can grade a reference or a counter-example
    without provisioning a workspace for each. It is the same function the
    grader calls, so the two cannot disagree.
    """
    return Verdict(
        reports=(
            definition_report(query),
            *(containers.evaluate(check, query) for check in spec.checks),
        )
    )


def definition_report(query: BuildQuery) -> CheckReport:
    """The synthesised `definition-parsed` check. Always present, always required.

    The error is the parser's own sentence, with a line number, in `actual`.
    """
    error = query.error()
    return CheckReport(
        check_id=DEFINITION_CHECK_ID,
        label="Docker could read your definition.",
        severity=Severity.REQUIRED,
        passed=error is None,
        expected="a definition the builder accepts",
        actual="it parsed" if error is None else error,
        explanation=(
            None
            if error is None
            else (
                "The checks below ran anyway, against whatever could be read "
                "before the error."
            )
        ),
    )
