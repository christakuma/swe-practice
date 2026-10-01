"""The grader over a real subprocess, end to end but below the use cases.

The unit suite proves the mapping against canned records and this proves the two
halves meet: that what the real plugin writes is what the real mapping reads.
A fake can agree with a grader about a shape they are both wrong about, and this
is the test that would notice.

Three cases only. More would be re-testing the mapping through a slower door.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.kata import KataGrader
from practice.adapters.kata.grader import COMPLEXITY_CHECK_ID
from practice.domain.attempt import Attempt, AttemptPolicy, ComplexityClaim
from practice.domain.ids import AttemptId
from practice.domain.verdict import Outcome
from tests.fakes import FakeClock

if TYPE_CHECKING:
    from practice.adapters.kata import PytestKataRunner
    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.exercise import Exercise


def an_attempt(
    exercise: Exercise, source: str, *, claim: ComplexityClaim | None = None
) -> Attempt:
    clock = FakeClock()
    attempt = Attempt(
        attempt_id=AttemptId.parse("aabbccdd-0000-4000-8000-000000000001"),
        exercise_id=exercise.id,
        policy=AttemptPolicy.for_exercise(exercise),
        started_at=clock.now(),
    )
    attempt.save_solution(source, at=clock.now())
    if claim is not None:
        attempt.declare_complexity(claim)
    return attempt


def test_the_reference_solution_earns_a_clean_pass(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    kata: Exercise,
    reference: str,
) -> None:
    """With the complexity declared to match, so the outcome is `PASS` rather
    than `PASS_WITH_ADVISORIES` — which is itself the assertion that the
    advisory only fires when there is something to reconcile.
    """
    grader = KataGrader(runner)
    attempt = an_attempt(
        kata, reference, claim=ComplexityClaim(time="O(n)", space="O(n)")
    )

    verdict = grader.grade(kata, workspace, attempt)

    assert verdict.outcome is Outcome.PASS
    assert verdict.failures == ()
    assert [report.check_id for report in verdict.reports][-1] == COMPLEXITY_CHECK_ID


def test_every_label_in_a_real_verdict_is_a_sentence(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    kata: Exercise,
    reference: str,
) -> None:
    """The docstrings survive the whole round trip — harvested at collection in
    one process, read out of JSON in another, and printed as the thing a solver
    actually reads.
    """
    verdict = KataGrader(runner).grade(kata, workspace, an_attempt(kata, reference))

    labels = [report.label for report in verdict.reports]
    assert all(label.endswith(".") for label in labels), labels
    assert all("_" not in label for label in labels), labels


def test_the_stub_fails_every_required_check(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    kata: Exercise,
    stub: str,
) -> None:
    verdict = KataGrader(runner).grade(kata, workspace, an_attempt(kata, stub))

    assert verdict.outcome is Outcome.FAIL
    assert len(verdict.failures) == len(
        [report for report in verdict.reports if report.is_required]
    )
    assert all(
        report.explanation == "NotImplementedError" for report in verdict.failures
    )
