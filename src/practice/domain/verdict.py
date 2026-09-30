"""The vocabulary a grading pass reports in.

`CheckReport` and `Verdict` — the assembly — are added alongside the ports; this
module starts with the two enumerations, because `CheckSpec` in `exercise.py`
needs `Severity` to exist before anything can be graded at all.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["Outcome", "Severity"]


class Severity(StrEnum):
    """How much a failing check matters.

    `ADVISORY` is the feature that makes the tool worth using (PLAN.md §4.4). It
    means *you achieved the goal, but the way you did it has consequences* —
    force-pushing a shared branch, reaching for `reset --hard` where `revert` was
    called for. Correctness and craft, graded separately.
    """

    REQUIRED = "required"
    ADVISORY = "advisory"


class Outcome(StrEnum):
    """The single derived result of a verdict.

    Derived, never set: see `Verdict.outcome`. Values match the YAML and the
    persisted form so no mapping table is needed at either boundary.
    """

    # bandit's S105 reads any constant named PASS* as a hardcoded password. It is
    # a false positive on an enum of grading outcomes, and the alternative —
    # renaming to PASSED — would distort the domain vocabulary to appease a
    # substring match.
    PASS = "pass"  # noqa: S105
    PASS_WITH_ADVISORIES = "pass_with_advisories"  # noqa: S105
    FAIL = "fail"
