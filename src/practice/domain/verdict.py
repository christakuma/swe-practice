"""What a grading pass produces: one report per check, and the verdict over them.

The interesting property is that `Outcome` is *derived*, never assigned. There is
no code path that can build a verdict claiming to pass while a required check
failed, because nothing stores the answer — `Verdict.outcome` computes it from the
reports every time it is asked.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from practice.domain.errors import InvalidValueError

if TYPE_CHECKING:
    from practice.domain.exercise import CheckSpec

__all__ = ["CheckReport", "Outcome", "Severity", "Verdict"]


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


@dataclass(frozen=True, slots=True)
class CheckReport:
    """The result of evaluating one `CheckSpec`.

    `label` and `explanation` are the content author's words, carried through
    unchanged — the engine never writes prose about an exercise it knows nothing
    about. `expected` and `actual` are display strings rather than typed values on
    purpose: a missing ref reports `actual="<ref does not exist>"`, which no
    `Sha | None` could represent, and a traceback in the verdict panel teaches
    nothing (PLAN.md §6.5).
    """

    check_id: str
    label: str
    severity: Severity
    passed: bool
    expected: str | None = None
    actual: str | None = None
    explanation: str | None = None

    @classmethod
    def from_spec(
        cls,
        spec: CheckSpec,
        *,
        passed: bool,
        expected: str | None = None,
        actual: str | None = None,
    ) -> CheckReport:
        """Build a report from the spec that produced it.

        The 19 assertion functions each end in a call to this, so none of them can
        forget to carry the author's label, severity or explanation across — and
        none of them has to know how.
        """
        return cls(
            check_id=spec.id,
            label=spec.label,
            severity=spec.severity,
            passed=passed,
            expected=expected,
            actual=actual,
            explanation=spec.explanation,
        )

    @property
    def is_required(self) -> bool:
        return self.severity is Severity.REQUIRED

    @property
    def is_blocking(self) -> bool:
        """A required check that failed — the only kind that can fail an attempt."""
        return self.is_required and not self.passed


@dataclass(frozen=True, slots=True)
class Verdict:
    """Every check that ran, in the order the exercise declares them."""

    reports: tuple[CheckReport, ...]

    def __post_init__(self) -> None:
        if not self.reports:
            raise InvalidValueError("a verdict needs at least one check report")
        ids = [report.check_id for report in self.reports]
        duplicates = sorted({name for name in ids if ids.count(name) > 1})
        if duplicates:
            raise InvalidValueError(
                f"duplicate check ids in verdict: {', '.join(duplicates)}"
            )

    @property
    def outcome(self) -> Outcome:
        """Pure derivation, and total: a non-empty verdict always has an outcome.

        Requiring at least one report is what makes it total. An empty verdict would
        have to be called a pass or a fail, and both answers are wrong — which is
        the argument for refusing to construct one at all.
        """
        if any(report.is_blocking for report in self.reports):
            return Outcome.FAIL
        if self.advisories:
            return Outcome.PASS_WITH_ADVISORIES
        return Outcome.PASS

    @property
    def failures(self) -> tuple[CheckReport, ...]:
        """Failed required checks: what has to change before this counts."""
        return tuple(report for report in self.reports if report.is_blocking)

    @property
    def advisories(self) -> tuple[CheckReport, ...]:
        """Failed advisory checks: you got there, and here is the cost."""
        return tuple(
            report
            for report in self.reports
            if not report.is_required and not report.passed
        )

    @property
    def passed(self) -> bool:
        """True for a pass with advisories too — the goal was met either way."""
        return self.outcome is not Outcome.FAIL
