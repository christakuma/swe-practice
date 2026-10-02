"""`SubmitScenario`: grade the repository as the solver left it, then close up.

Mostly about ordering, like `SubmitSolution` — and the one ordering that matters more
here is disposal. For a kata, disposing of a workspace after a failed grading pass
costs a lost pytest run. For a scenario it destroys a repository the solver spent
twenty commands building, which is both their work and the only artifact that could
explain why grading failed.
"""

from __future__ import annotations

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    UnsupportedExerciseKindError,
    WorkspaceGoneError,
)
from practice.application.registry import GraderRegistry
from practice.domain.attempt import AttemptStatus
from practice.domain.errors import AttemptStateError
from practice.domain.exercise import ExerciseKind
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.verdict import Outcome
from tests.unit.application.helpers import (
    ExplodingGrader,
    NullGrader,
    a_run_scenario_command,
    a_start_attempt,
    a_submit_scenario,
    an_environment,
)

SCENARIO = ExerciseId("git/revert-a-pushed-commit")


def test_it_grades_the_attempt_and_completes_it() -> None:
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    submission = a_submit_scenario(world)(started.attempt.id)

    assert submission.outcome is Outcome.PASS
    assert submission.attempt.status is AttemptStatus.COMPLETED
    assert submission.attempt.verdict is submission.verdict


def test_it_grades_with_the_scenario_grader_not_the_kata_one() -> None:
    """Which is what the kind registry is for. A kata-shaped verdict for a git
    scenario is worse than no verdict at all.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    a_submit_scenario(world)(started.attempt.id)

    assert len(world.scenario_recorder.calls) == 1
    assert world.recorder.calls == []


def test_the_grader_sees_every_command_the_attempt_ran() -> None:
    """There is nothing to save before grading -- the repository is already on disk --
    and the equivalent guarantee is that `RunScenarioCommand` recorded each command
    as it ran. A verdict is still derived from something persisted and replayable;
    the persisting happened earlier.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)
    run = a_run_scenario_command(world)
    run(started.attempt.id, "git status")
    run(started.attempt.id, "git revert --no-edit HEAD")

    a_submit_scenario(world)(started.attempt.id)

    _, events_at_grading, _ = world.scenario_recorder.calls[0]
    assert events_at_grading == 2


def test_the_workspace_is_disposed_on_success() -> None:
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    a_submit_scenario(world)(started.attempt.id)

    assert world.provisioner.workspaces[started.attempt.id].disposed is True


def test_it_grades_before_it_disposes() -> None:
    """Not merely "both happened". A grader handed a disposed workspace would run
    `git` against a directory that is not there and report every check as a clean
    failure -- which looks exactly like a solver getting everything wrong.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    a_submit_scenario(world)(started.attempt.id)

    _, _, disposed_at_grading = world.scenario_recorder.calls[0]
    assert disposed_at_grading is False


def test_a_failed_grading_pass_leaves_the_workspace_and_the_attempt_alone() -> None:
    """The decision this use case exists to get right. Disposal is not in a
    `finally`: if grading raises, the attempt is still ACTIVE, and PLAN.md §8.1 ties
    workspace lifetime to exactly that. Deleting it here would destroy the
    repository the solver built *and* the only thing that could explain the failure,
    and leave an active attempt nothing can submit or resume.
    """
    world = an_environment(scenario_grader=ExplodingGrader())
    started = a_start_attempt(world)(SCENARIO)

    with pytest.raises(RuntimeError, match="grader exploded"):
        a_submit_scenario(world)(started.attempt.id)

    assert world.provisioner.workspaces[started.attempt.id].disposed is False
    assert started.attempt.status is AttemptStatus.ACTIVE
    assert started.attempt.verdict is None


def test_it_saves_the_completed_attempt() -> None:
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    a_submit_scenario(world)(started.attempt.id)

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.status is AttemptStatus.COMPLETED


class TestRefusals:
    def test_an_attempt_that_does_not_exist_is_refused(self) -> None:
        world = an_environment()

        with pytest.raises(AttemptNotFoundError):
            a_submit_scenario(world)(
                AttemptId.parse("00000000-0000-4000-8000-000000000999")
            )

    def test_a_library_that_changed_under_a_live_attempt_is_refused(self) -> None:
        """Rare, and worth a distinct error: the attempt is now ungradable and the
        only honest thing to do with it is abandon it.
        """
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)
        world.content.forget(SCENARIO)

        with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
            a_submit_scenario(world)(started.attempt.id)

    def test_a_collected_workspace_is_refused_with_its_own_error(self) -> None:
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)
        world.provisioner.collect(started.attempt.id)

        with pytest.raises(WorkspaceGoneError, match="abandon it"):
            a_submit_scenario(world)(started.attempt.id)

    def test_an_unregistered_kind_is_refused_before_the_workspace_is_touched(
        self,
    ) -> None:
        """Which is also why the grader is looked up before `attach`: a registry
        miss should not leave a workspace half-interrogated.
        """
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)
        submit = a_submit_scenario(
            world, graders=GraderRegistry(graders={ExerciseKind.KATA: NullGrader()})
        )

        with pytest.raises(UnsupportedExerciseKindError):
            submit(started.attempt.id)

        assert world.provisioner.workspaces[started.attempt.id].disposed is False

    def test_an_attempt_cannot_be_submitted_twice(self) -> None:
        """And the refusal names the real reason. This is the use case a
        double-clicked submit button calls, and without the status guard it reaches
        `attach`, finds the workspace disposed, and tells a solver to abandon an
        attempt that has just passed.
        """
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)
        submit = a_submit_scenario(world)
        submit(started.attempt.id)

        with pytest.raises(AttemptStateError, match="completed"):
            submit(started.attempt.id)

        assert len(world.scenario_recorder.calls) == 1, "it graded twice"
