"""Submitting a solution: save it, grade it, and on a pass close it and free the disk.

The use case that touches every port, so most of this file is about *order* and
about what happens when one step fails. Three of these tests pin decisions that
PLAN.md §8.1 makes about workspace lifetime, and would pass just as happily
against an implementation that got them backwards if they only checked the
happy path.
"""

from __future__ import annotations

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.attempt import AttemptStatus, ComplexityClaim
from practice.domain.errors import AttemptStateError
from practice.domain.exercise import ComplexityExpectation
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.verdict import Outcome
from tests.unit.application.helpers import (
    ExplodingGrader,
    RecordingGrader,
    a_failing_verdict,
    a_start_attempt,
    a_submit_solution,
    an_environment,
)

KATA = ExerciseId("katas/two-sum")
SOURCE = "def two_sum(numbers, target):\n    return (0, 1)\n"


def test_it_grades_the_source_and_completes_the_attempt() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    submission = a_submit_solution(world)(started.attempt.id, SOURCE)

    assert submission.outcome is Outcome.PASS
    assert submission.passed
    assert submission.attempt.status is AttemptStatus.COMPLETED
    assert submission.attempt.verdict is submission.verdict
    assert submission.exercise.id == KATA


def test_the_completed_attempt_is_saved() -> None:
    """The in-memory store holds a snapshot, so an attempt that was mutated and
    not saved reads back as still active — which is what makes this assertion
    about `save` rather than about aliasing.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    a_submit_solution(world)(started.attempt.id, SOURCE)

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.status is AttemptStatus.COMPLETED
    assert stored.verdict is not None


def test_the_source_reaches_the_attempt_log_before_it_is_graded() -> None:
    """A verdict is derived from something persisted and replayable, never from
    an argument that was only ever in memory.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    a_submit_solution(world)(started.attempt.id, SOURCE)

    graded_source, events_at_grading, disposed_at_grading = world.recorder.calls[0]
    assert graded_source == SOURCE
    assert events_at_grading == 1
    assert not disposed_at_grading, "the workspace was disposed before grading"


def test_a_declared_complexity_is_recorded_and_compared() -> None:
    world = an_environment(
        complexity=ComplexityExpectation(expected_time="O(n)", expected_space="O(n)")
    )
    started = a_start_attempt(world)(KATA)
    claim = ComplexityClaim(time="O(n)", space="O(n)")

    submission = a_submit_solution(world)(started.attempt.id, SOURCE, complexity=claim)

    assert submission.attempt.declared_complexity == claim


def test_the_workspace_is_disposed_on_a_successful_submission() -> None:
    """§8.1: a workspace lives exactly as long as its attempt is active."""
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    a_submit_solution(world)(started.attempt.id, SOURCE)

    assert world.provisioner.workspace_for(started.attempt.id).disposed


def test_a_failing_verdict_leaves_the_attempt_open_and_its_workspace() -> None:
    """ADR 0029, and the test this file used to state the opposite of.

    A wrong answer was a finished attempt until a solver pressed Submit again
    and was told the attempt was completed. Now the failure is logged and the
    attempt stays open -- and the workspace stays with it, because the next
    submission is about to be graded in it.
    """
    world = an_environment(grader=RecordingGrader(a_failing_verdict()))
    started = a_start_attempt(world)(KATA)

    submission = a_submit_solution(world)(started.attempt.id, SOURCE)

    assert submission.outcome is Outcome.FAIL
    assert not submission.closed
    assert submission.tries == 1
    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.status is AttemptStatus.ACTIVE
    assert [event.verdict for event in stored.failed_submissions] == [
        submission.verdict
    ]
    assert not world.provisioner.workspace_for(started.attempt.id).disposed


def test_a_failed_attempt_takes_another_submission() -> None:
    """The point of the change: the second press of Submit is graded, not refused.

    Two submissions into one workspace, and the second one's source is what the
    grader saw -- which is `latest_source` reading the last `SolutionSaved` of
    two, rather than the only one.
    """
    world = an_environment(grader=RecordingGrader(a_failing_verdict()))
    started = a_start_attempt(world)(KATA)
    submit = a_submit_solution(world)

    submit(started.attempt.id, "def two_sum(numbers, target):\n    return None\n")
    second = submit(started.attempt.id, SOURCE)

    assert second.tries == 2
    assert not second.closed
    grader = world.grader
    assert isinstance(grader, RecordingGrader)
    assert [source for source, _, _ in grader.calls][-1] == SOURCE


def test_a_pass_after_a_failure_closes_and_disposes() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    attempt = world.attempts.get(started.attempt.id)
    assert attempt is not None
    attempt.submit(a_failing_verdict(), at=world.clock.now())
    world.attempts.save(attempt)

    submission = a_submit_solution(world)(started.attempt.id, SOURCE)

    assert submission.closed
    assert submission.passed
    assert submission.tries == 2
    assert world.provisioner.workspace_for(started.attempt.id).disposed


def test_a_grader_that_raises_leaves_the_workspace_alone() -> None:
    """Not a `finally`, deliberately. The attempt is still active, so §8.1 says
    its workspace lives — and it is the only thing that could explain the
    failure. Disposing here would destroy the evidence and leave an active
    attempt that can never be submitted or resumed.
    """
    world = an_environment(grader=ExplodingGrader())
    started = a_start_attempt(world)(KATA)

    with pytest.raises(RuntimeError, match="grader exploded"):
        a_submit_solution(world)(started.attempt.id, SOURCE)

    workspace = world.provisioner.workspace_for(started.attempt.id)
    assert not workspace.disposed
    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.status is AttemptStatus.ACTIVE


def test_an_unknown_attempt_is_refused() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError):
        a_submit_solution(world)(
            AttemptId.parse("ffffffff-0000-4000-8000-000000000000"), SOURCE
        )


def test_an_exercise_removed_under_a_live_attempt_is_refused() -> None:
    """The library changed while someone was working: renamed or deleted. The
    attempt is now ungradable, and saying so beats a crash — the only honest
    thing left to do with it is abandon it.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.content.forget(KATA)

    with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
        a_submit_solution(world)(started.attempt.id, SOURCE)


def test_a_collected_workspace_is_refused_rather_than_reprovisioned() -> None:
    """Re-provisioning would run the fixture again and grade a repository the
    solver never touched, which is worse than failing: it would produce a
    verdict about nothing and call the attempt finished.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.collect(started.attempt.id)

    with pytest.raises(WorkspaceGoneError, match="no longer on disk"):
        a_submit_solution(world)(started.attempt.id, SOURCE)


def test_a_second_submission_is_refused_for_being_a_second_submission() -> None:
    """Which guard fires first is worth pinning rather than guessing, and this test
    used to pin the wrong one.

    Before Phase 5 the answer was `WorkspaceGoneError`: a successful submission
    disposes of the workspace, so the second call reached `attach` and found
    nothing. The ordering was right and what it produced was not — the message tells
    a solver to *abandon the attempt and start again*, about an attempt that had
    just been graded successfully. `Attempt.complete` refuses the second call with
    the right message and was simply never reached, so the use case checks the
    status itself now.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    submit = a_submit_solution(world)
    submit(started.attempt.id, SOURCE)

    with pytest.raises(AttemptStateError, match="completed"):
        submit(started.attempt.id, SOURCE)

    assert len(world.recorder.calls) == 1, "it graded twice"
