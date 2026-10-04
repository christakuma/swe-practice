"""Running one drill assertion, the way the dispatcher will.

The drill counterpart of `tests/unit/domain/checks/helpers.py`, and it goes
through `drills.registry.evaluate` rather than calling the function directly.
That is the whole point of it: every case below then exercises negation, the
author's label and the misconfiguration path at the same time as the assertion,
so none of the ten can quietly stop being dispatchable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from practice.domain.drills import registry
from practice.domain.exercise import CheckSpec
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.exercise import ParamValue
    from practice.domain.ports import DrillQuery
    from practice.domain.verdict import CheckReport


def run(
    assertion: str,
    query: DrillQuery,
    *,
    negated: bool = False,
    **params: Any,
) -> CheckReport:
    """Evaluate one assertion against a fake and hand back the report.

    `**params` rather than a mapping argument, so a case reads as
    `run("table_row_count", db, table="orders", equals=2)` — which is very close
    to the YAML an author writes, and the resemblance is deliberate: a test that
    looks like the content it is defending is a test somebody will keep correct.
    """
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
