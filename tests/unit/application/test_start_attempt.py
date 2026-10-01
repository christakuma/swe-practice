"""Starting an attempt: what gets built, in what order, and what refuses.

All fakes, so the whole file is milliseconds — which is the point of the ports.
The ordering assertions are the ones that matter: two of them encode decisions
that are invisible in the happy path and only observable when something fails
halfway (PLAN.md §8.1).
"""

from __future__ import annotations

import pytest

from practice.application.errors import (
    ExerciseNotFoundError,
    UnsupportedExerciseKindError,
)
from practice.application.registry import GraderRegistry
from practice.application.use_cases import StartAttempt
from practice.domain.attempt import AttemptStatus
from practice.domain.exercise import ExerciseKind
from practice.domain.ids import ExerciseId
from tests.unit.application.helpers import (
    FailingProvisioner,
    NullGrader,
    a_start_attempt,
    an_environment,
)


def test_it_provisions_a_workspace_and_remembers_the_attempt() -> None:
    world = an_environment()
    start = a_start_attempt(world)

    started = start(ExerciseId("katas/two-sum"))

    assert started.attempt.status is AttemptStatus.ACTIVE
    assert started.exercise.id == ExerciseId("katas/two-sum")
    assert started.prompt == started.exercise.prompt
    assert world.provisioner.provisioned == [("katas/two-sum", started.attempt.id)]
    assert world.attempts.get(started.attempt.id) is not None


def test_the_attempt_carries_the_exercise_policy() -> None:
    """`AttemptPolicy.for_exercise` is what lets the aggregate enforce its own
    rules, so the use case has to copy it in — a kata gets a zero command budget
    and an empty allowlist, which is the honest encoding of having no console.
    """
    started = a_start_attempt(an_environment())(ExerciseId("katas/two-sum"))

    assert started.attempt.policy.max_commands == 0
    assert started.attempt.policy.allowed_commands == frozenset()
    assert started.attempt.policy.hint_count == 1


def test_it_starts_the_attempt_at_the_clock_it_was_given() -> None:
    world = an_environment()

    started = a_start_attempt(world)(ExerciseId("katas/two-sum"))

    assert started.attempt.started_at == world.clock.now()


def test_an_unknown_exercise_is_refused_before_anything_is_built() -> None:
    world = an_environment()

    with pytest.raises(ExerciseNotFoundError, match="katas/nope"):
        a_start_attempt(world)(ExerciseId("katas/nope"))

    assert world.provisioner.provisioned == []
    assert len(world.attempts) == 0


def test_an_ungradable_kind_is_refused_before_the_fixture_runs() -> None:
    """The ordering decision. Provisioning a git scenario runs its fixture and
    builds a repository; discovering afterwards that nothing can grade the
    result wastes the work *and* leaves a workspace for an attempt that can
    never be completed.
    """
    world = an_environment()

    with pytest.raises(UnsupportedExerciseKindError, match="phase 5"):
        a_start_attempt(world)(ExerciseId("git/revert-a-pushed-commit"))

    assert world.provisioner.provisioned == []
    assert len(world.attempts) == 0


def test_a_registered_scenario_grader_would_be_allowed_to_start() -> None:
    """The refusal above has to be about the missing grader, not about the kind.
    Register one and the same exercise provisions — otherwise the test passes
    for a reason that would survive Phase 5 and block it.
    """
    world = an_environment()
    start = a_start_attempt(
        world,
        graders=GraderRegistry(
            graders={
                ExerciseKind.KATA: NullGrader(),
                ExerciseKind.GIT_SCENARIO: NullGrader(),
            }
        ),
    )

    started = start(ExerciseId("git/revert-a-pushed-commit"))

    assert started.attempt.policy.max_commands == 25


def test_the_id_comes_from_the_generator_port() -> None:
    """Injected rather than generated in the aggregate, so a test can assert on
    a readable id instead of random hex (PLAN.md §4.6).
    """
    world = an_environment()
    start = a_start_attempt(world)

    first = start(ExerciseId("katas/two-sum"))
    second = start(ExerciseId("katas/two-sum"))

    assert first.attempt.id.short == "00000000"
    assert second.attempt.id.short == "00000000"
    assert first.attempt.id != second.attempt.id


def test_a_failed_provision_leaves_no_attempt_behind() -> None:
    """The second ordering decision, from the other side.

    The workspace is provisioned *before* the attempt is saved, so a provision
    that blows up leaves nothing: no attempt row the resume prompt would offer
    and nothing could resume. The reverse order would leave exactly that.
    """
    world = an_environment()
    start = StartAttempt(
        content=world.content,
        attempts=world.attempts,
        provisioner=FailingProvisioner(),
        graders=world.graders,
        clock=world.clock,
        ids=world.ids,
    )

    with pytest.raises(RuntimeError, match="fixture exploded"):
        start(ExerciseId("katas/two-sum"))

    assert len(world.attempts) == 0
