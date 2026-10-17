"""Running one container assertion through the dispatcher, the way grading does.

The container counterpart of `tests/unit/domain/drills/helpers.py`: every case
goes through `registry.evaluate`, so negation, the author's label and the
misconfiguration path are exercised alongside each assertion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from practice.domain.containers import registry
from practice.domain.exercise import CheckSpec
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.exercise import ParamValue
    from practice.domain.ports import BuildQuery
    from practice.domain.verdict import CheckReport


def run(
    assertion: str,
    query: BuildQuery,
    *,
    negated: bool = False,
    **params: Any,
) -> CheckReport:
    """`run("runs_as", image, pattern="^root")`, which reads like the YAML."""
    values: Mapping[str, ParamValue] = params
    return registry.evaluate(
        CheckSpec(
            id="a-check",
            label="The label the author wrote.",
            severity=Severity.REQUIRED,
            assertion=assertion,
            params=values,
            negated=negated,
            explanation="Why it matters.",
        ),
        query,
    )
