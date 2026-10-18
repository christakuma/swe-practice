"""A container definition becomes a verdict. `SqlDrillGrader`'s counterpart.

Satisfies `practice.domain.ports.Grader` for `ExerciseKind.CONTAINER`, and makes
the same three decisions the drill grader does, for the same reasons:

* **`definition-parsed` is a synthesised required check, and it comes first.**
  A Dockerfile with an unknown instruction produces no stages, so there is
  nothing for a declared check to read, and *eight failures* for one typo tells
  the solver they are wrong in eight ways. The declared checks are still
  reported, each as failed for want of a definition, and a negated one is not
  allowed to pass on nothing (`registry.evaluate`).
* **The editable file comes from the attempt's log**, through `latest_source`,
  and the rest of the build context from the content library, never from the
  workspace. The workspace is the solver's to change, and the first version
  read the context from it: deleting `.env` there, or adding a `.dockerignore`
  that names it, passed the secrets exercise with the stub untouched. The one
  file the solver may change is the one the attempt remembers.
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
    from pathlib import Path

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
    """Satisfies `practice.domain.ports.Grader` for `ExerciseKind.CONTAINER`.

    Takes the content root because the build context is the library's, not
    the workspace's: see the module docstring for the attempt that proved it.
    """

    __slots__ = ("_content_root",)

    def __init__(self, content_root: Path) -> None:
        self._content_root = content_root

    def grade(
        self,
        exercise: Exercise,
        workspace: Workspace,  # noqa: ARG002 - the port's; unread on purpose
        attempt: Attempt,
    ) -> Verdict:
        """Read the shipped context, overlay the saved answer, evaluate every check.

        `workspace` is unread, deliberately: everything a verdict depends on is
        either the library's or the attempt's.
        """
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
        root = self._content_root / exercise.id.value / spec.context
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
                "The checks below could not read anything either, so each is "
                "reported as failed until this one passes."
            )
        ),
    )
