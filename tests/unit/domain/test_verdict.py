"""Verdict assembly, and the outcome derivation that is the whole point of it."""

from __future__ import annotations

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.exercise import CheckSpec
from practice.domain.verdict import CheckReport, Outcome, Severity, Verdict


def a_report(
    check_id: str = "content-restored",
    *,
    severity: Severity = Severity.REQUIRED,
    passed: bool = True,
) -> CheckReport:
    return CheckReport(
        check_id=check_id,
        label=f"the {check_id} check",
        severity=severity,
        passed=passed,
    )


class TestCheckReport:
    def test_from_spec_carries_the_authors_words_across(self) -> None:
        spec = CheckSpec(
            id="history-preserved",
            label="The bad commit is still reachable",
            severity=Severity.REQUIRED,
            assertion="is_ancestor",
            explanation="Your teammate already has c3.",
        )

        report = CheckReport.from_spec(
            spec, passed=False, expected="an ancestor of HEAD", actual="unreachable"
        )

        assert report.check_id == "history-preserved"
        assert report.label == "The bad commit is still reachable"
        assert report.severity is Severity.REQUIRED
        assert report.explanation == "Your teammate already has c3."
        assert report.expected == "an ancestor of HEAD"
        assert report.actual == "unreachable"
        assert report.passed is False

    def test_only_a_failed_required_check_blocks(self) -> None:
        assert a_report(passed=False).is_blocking is True
        assert a_report(passed=True).is_blocking is False
        assert a_report(severity=Severity.ADVISORY, passed=False).is_blocking is False

    def test_expected_and_actual_are_display_strings_so_a_missing_ref_fits(
        self,
    ) -> None:
        """A missing ref is a clean failure, never an error (PLAN.md §6.5)."""
        report = a_report(passed=False)
        described = CheckReport(
            check_id=report.check_id,
            label=report.label,
            severity=report.severity,
            passed=False,
            expected="refs/remotes/origin/main == HEAD",
            actual="<ref does not exist>",
        )

        assert described.actual == "<ref does not exist>"


class TestOutcomeDerivation:
    def test_all_checks_passing_is_a_pass(self) -> None:
        verdict = Verdict((a_report("one"), a_report("two")))

        assert verdict.outcome is Outcome.PASS
        assert verdict.passed is True
        assert verdict.failures == ()
        assert verdict.advisories == ()

    def test_a_failed_advisory_alone_is_a_pass_with_advisories(self) -> None:
        verdict = Verdict(
            (
                a_report("content-restored"),
                a_report("no-force-push", severity=Severity.ADVISORY, passed=False),
            )
        )

        assert verdict.outcome is Outcome.PASS_WITH_ADVISORIES
        assert verdict.passed is True
        assert [report.check_id for report in verdict.advisories] == ["no-force-push"]

    def test_a_failed_required_check_fails_the_attempt(self) -> None:
        verdict = Verdict((a_report("content-restored", passed=False),))

        assert verdict.outcome is Outcome.FAIL
        assert verdict.passed is False
        assert [report.check_id for report in verdict.failures] == ["content-restored"]

    def test_a_required_failure_outranks_a_passing_advisory(self) -> None:
        verdict = Verdict(
            (
                a_report("content-restored", passed=False),
                a_report("no-force-push", severity=Severity.ADVISORY),
            )
        )

        assert verdict.outcome is Outcome.FAIL

    def test_a_required_failure_outranks_an_advisory_failure_too(self) -> None:
        verdict = Verdict(
            (
                a_report("content-restored", passed=False),
                a_report("no-force-push", severity=Severity.ADVISORY, passed=False),
            )
        )

        assert verdict.outcome is Outcome.FAIL
        assert len(verdict.failures) == 1
        assert len(verdict.advisories) == 1

    def test_the_outcome_is_derived_not_stored(self) -> None:
        """There is no constructor argument that could claim a pass while a required
        check failed, which is the property this whole type exists for.
        """
        assert "outcome" not in set(Verdict.__dataclass_fields__)


class TestVerdictInvariants:
    def test_a_verdict_needs_at_least_one_report(self) -> None:
        """Otherwise the derivation is not total: an empty verdict would have to be
        called a pass or a fail, and both answers are wrong.
        """
        with pytest.raises(InvalidValueError, match="at least one check report"):
            Verdict(())

    def test_rejects_duplicate_check_ids(self) -> None:
        with pytest.raises(InvalidValueError, match="duplicate check ids"):
            Verdict((a_report("clean"), a_report("clean", passed=False)))

    def test_reports_keep_the_order_the_exercise_declares_them_in(self) -> None:
        verdict = Verdict((a_report("third"), a_report("first"), a_report("second")))

        assert [report.check_id for report in verdict.reports] == [
            "third",
            "first",
            "second",
        ]
