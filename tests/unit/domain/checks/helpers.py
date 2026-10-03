"""One way to run a check in a test, so 20 assertions do not each invent one.

Every assertion is exercised through `run` — the same `registry.evaluate` the real
grader calls — rather than by calling the function directly. That is deliberate:
calling the function would skip negation, skip the author's label and skip the
`CheckSpecError` handling, which are three of the things most worth testing and all
three live in the dispatcher.

The `CheckSpec` these build is a real one, so a test that writes a malformed id or
an unregistered assertion name fails on the domain's own invariants rather than
proving something about a shape that cannot exist.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from practice.domain.attempt import Attempt, AttemptPolicy, CommandResult
from practice.domain.checks import registry
from practice.domain.exercise import CheckSpec, Hint
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.exercise import ParamValue
    from practice.domain.ports import RepoQuery
    from practice.domain.verdict import CheckReport

__all__ = ["an_attempt", "run", "spec"]

#: A fixed instant, because `Attempt` refuses a naive datetime and refuses to go
#: backwards. Nothing here is about time.
_AT = datetime(2026, 3, 4, 9, 0, tzinfo=UTC)


def spec(
    assertion: str,
    *,
    check_id: str = "the-check",
    severity: Severity = Severity.REQUIRED,
    negated: bool = False,
    explanation: str | None = "Why this matters.",
    **params: Any,
) -> CheckSpec:
    """A `CheckSpec`, with the `with:` mapping as keyword arguments.

    Keywords because that is what a test reads best — `spec("is_ancestor",
    ancestor="@c1", descendant="HEAD")` is the YAML, in Python. A parameter whose
    name collides with one of the named arguments above is the one case this cannot
    express, and there is none in the vocabulary.
    """
    return CheckSpec(
        id=check_id,
        label="The thing the author said.",
        severity=severity,
        assertion=assertion,
        params=_as_params(params),
        negated=negated,
        explanation=explanation,
    )


def run(
    query: RepoQuery,
    assertion: str,
    *,
    attempt: Attempt | None = None,
    **kwargs: Any,
) -> CheckReport:
    """Evaluate one assertion the way the grader does, and hand back its report."""
    return registry.evaluate(
        spec(assertion, **kwargs),
        query,
        attempt if attempt is not None else an_attempt(),
    )


def an_attempt(
    commands: Sequence[Sequence[str]] = (),
    *,
    max_commands: int = 25,
    allowed: frozenset[str] = frozenset({"git", "cat", "ls", "write"}),
) -> Attempt:
    """An attempt whose log holds the given commands, for the process assertions.

    Built by driving the real aggregate rather than by poking at its internals, so
    a command the exercise would not allow cannot get into a test's log — which is
    the invariant `record_command` exists to hold, and a test that bypassed it would
    be asserting about a log the product cannot produce.
    """
    attempt = Attempt(
        attempt_id=AttemptId.parse("3f2a1b0c-0000-4000-8000-000000000001"),
        exercise_id=ExerciseId("git/revert-a-pushed-commit"),
        policy=AttemptPolicy(
            max_commands=max_commands,
            hints=(Hint("Look before you leap."),),
            allowed_commands=allowed,
        ),
        started_at=_AT,
    )
    for argv in commands:
        attempt.record_command(list(argv), CommandResult(exit_code=0), at=_AT)
    return attempt


def _as_params(params: Mapping[str, Any]) -> Mapping[str, ParamValue]:
    """Turn a test's keyword arguments into a `with:` mapping.

    Lists become tuples, because `ParamValue` is recursive over tuples and a list
    would be a type the domain does not model — the YAML loader hands tuples over
    for the same reason.
    """
    return {
        name: tuple(value) if isinstance(value, list) else value
        for name, value in params.items()
    }
