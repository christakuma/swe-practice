"""The two use cases ADR 0029 added: conceding a failed attempt, and Run.

Together because they are the two halves of what a failure now means. A
failing submission leaves the attempt open, so there has to be a way to stop
that is not `abandon` -- `ConcedeAttempt` -- and a way to check an answer that
does not spend a submission at all -- `TryExamples`. Plus the scenario's half
of the change to submission, which is the one with a repository at stake.
"""

from __future__ import annotations

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    UnsupportedExerciseKindError,
    WorkspaceGoneError,
)
from practice.domain.attempt import AttemptStatus
from practice.domain.errors import AttemptStateError
from practice.domain.exercise import Example
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.verdict import Outcome
from tests.fakes import FakeContentRepository, a_kata, a_scenario
from tests.unit.application.helpers import (
    RecordingGrader,
    World,
    a_concede_attempt,
    a_failing_verdict,
    a_run_scenario_command,
    a_start_attempt,
    a_submit_scenario,
    a_submit_solution,
    a_try_examples,
    an_environment,
)

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
SOURCE = "def two_sum(numbers, target):\n    return (0, 1)\n"
UNKNOWN = AttemptId.parse("99999999-0000-4000-8000-000000000000")


def with_examples(world: World) -> World:
    """The world's kata, given an example to run. The fake's has none, and a
    kata without examples is refused by Run before it reaches the runner."""
    world.content = FakeContentRepository(
        [
            a_kata(examples=(Example(input="two_sum([1, 2], 3)", output="(0, 1)"),)),
            a_scenario(),
        ]
    )
    return world


def a_world() -> World:
    return with_examples(an_environment())


def a_failing_world() -> World:
    """Both graders fail, chosen before the world is built."""
    return with_examples(
        an_environment(
            grader=RecordingGrader(a_failing_verdict()),
            scenario_grader=RecordingGrader(a_failing_verdict()),
        )
    )


def a_failed_kata(world: World) -> AttemptId:
    attempt_id = a_start_attempt(world)(KATA).attempt.id
    a_submit_solution(world)(attempt_id, SOURCE)
    return attempt_id


# --- a scenario's failed submission ------------------------------------------


def test_a_failed_scenario_keeps_its_repository_and_its_attempt() -> None:
    """The case the change was made for: the repository the solver spent
    twenty commands on is still there to fix."""
    world = a_failing_world()
    attempt_id = a_start_attempt(world)(SCENARIO).attempt.id
    a_run_scenario_command(world)(attempt_id, "git status")

    submission = a_submit_scenario(world)(attempt_id)

    assert submission.outcome is Outcome.FAIL
    assert not submission.closed
    assert not world.provisioner.workspace_for(attempt_id).disposed


def test_a_failed_scenario_takes_more_commands_and_a_second_submission() -> None:
    world = a_failing_world()
    attempt_id = a_start_attempt(world)(SCENARIO).attempt.id
    a_submit_scenario(world)(attempt_id)

    a_run_scenario_command(world)(attempt_id, "git revert --no-edit HEAD")
    second = a_submit_scenario(world)(attempt_id)

    assert second.tries == 2
    assert second.attempt.command_count == 1


# --- conceding ---------------------------------------------------------------


def test_conceding_closes_on_the_last_failure_and_saves_it() -> None:
    world = a_failing_world()
    attempt_id = a_failed_kata(world)

    conceded = a_concede_attempt(world)(attempt_id)

    assert conceded.closed
    assert not conceded.passed
    assert conceded.tries == 1
    stored = world.attempts.get(attempt_id)
    assert stored is not None
    assert stored.status is AttemptStatus.COMPLETED
    assert stored.verdict == conceded.verdict


def test_conceding_frees_the_workspace() -> None:
    """The attempt is no longer active, so §8.1 says its workspace goes."""
    world = a_failing_world()
    attempt_id = a_failed_kata(world)

    a_concede_attempt(world)(attempt_id)

    assert world.provisioner.discarded == [attempt_id.short]


def test_conceding_grades_nothing() -> None:
    """The verdict is one the log holds; a grading pass here would be a submit
    button with a different label."""
    world = a_failing_world()
    attempt_id = a_failed_kata(world)
    grader = world.grader
    assert isinstance(grader, RecordingGrader)
    graded = len(grader.calls)

    a_concede_attempt(world)(attempt_id)

    assert len(grader.calls) == graded


def test_an_attempt_that_has_not_failed_cannot_be_conceded() -> None:
    world = an_environment()
    attempt_id = a_start_attempt(world)(KATA).attempt.id

    with pytest.raises(AttemptStateError, match="no failed submission"):
        a_concede_attempt(world)(attempt_id)

    assert world.provisioner.discarded == []


def test_conceding_an_unknown_attempt_is_refused() -> None:
    with pytest.raises(AttemptNotFoundError):
        a_concede_attempt(an_environment())(UNKNOWN)


def test_conceding_an_attempt_whose_exercise_has_gone_leaves_it_untouched() -> None:
    """Refused before the save, so the stored attempt is still open -- and still
    abandonable, which is the way out that needs no exercise."""
    world = a_failing_world()
    attempt_id = a_failed_kata(world)
    world.content = FakeContentRepository([])

    with pytest.raises(ExerciseNotFoundError, match="abandon it instead"):
        a_concede_attempt(world)(attempt_id)

    stored = world.attempts.get(attempt_id)
    assert stored is not None
    assert stored.is_active
    assert world.provisioner.discarded == []


# --- Run ---------------------------------------------------------------------


def test_run_hands_the_source_to_the_runner_in_the_attempts_workspace() -> None:
    world = a_world()
    attempt_id = a_start_attempt(world)(KATA).attempt.id

    trial = a_try_examples(world)(attempt_id, SOURCE)

    assert trial is world.examples.trial
    assert world.examples.calls == [(str(KATA), SOURCE, False)]


def test_run_records_nothing() -> None:
    """Not a `SolutionSaved`, not a failure: ADR 0013's line, with a button."""
    world = a_world()
    attempt_id = a_start_attempt(world)(KATA).attempt.id

    a_try_examples(world)(attempt_id, SOURCE)

    stored = world.attempts.get(attempt_id)
    assert stored is not None
    assert stored.events == ()
    assert stored.is_active


def test_run_works_on_an_attempt_that_has_failed() -> None:
    """The order a solver actually goes in: submit, fail, run, fix, submit."""
    world = a_failing_world()
    attempt_id = a_failed_kata(world)

    a_try_examples(world)(attempt_id, SOURCE)

    assert len(world.examples.calls) == 1


def test_run_refuses_a_finished_attempt_before_reaching_the_workspace() -> None:
    """A passed attempt's workspace is gone, and *abandon it and start again*
    is the wrong sentence about an attempt that passed."""
    world = a_world()
    attempt_id = a_start_attempt(world)(KATA).attempt.id
    a_submit_solution(world)(attempt_id, SOURCE)

    with pytest.raises(AttemptStateError, match=r"cannot run: attempt .* is completed"):
        a_try_examples(world)(attempt_id, SOURCE)

    assert world.examples.calls == []


def test_run_refuses_a_scenario_by_name() -> None:
    world = a_world()
    attempt_id = a_start_attempt(world)(SCENARIO).attempt.id

    with pytest.raises(UnsupportedExerciseKindError, match="no examples to run"):
        a_try_examples(world)(attempt_id, "")

    assert world.examples.calls == []


def test_run_refuses_a_workspace_that_has_gone() -> None:
    world = a_world()
    attempt_id = a_start_attempt(world)(KATA).attempt.id
    world.provisioner.discard(attempt_id.short)

    with pytest.raises(WorkspaceGoneError):
        a_try_examples(world)(attempt_id, SOURCE)


def test_run_refuses_an_unknown_attempt() -> None:
    with pytest.raises(AttemptNotFoundError):
        a_try_examples(a_world())(UNKNOWN, SOURCE)


def test_run_refuses_an_attempt_whose_exercise_has_gone() -> None:
    world = a_world()
    attempt_id = a_start_attempt(world)(KATA).attempt.id
    world.content = FakeContentRepository([])

    with pytest.raises(ExerciseNotFoundError):
        a_try_examples(world)(attempt_id, SOURCE)
