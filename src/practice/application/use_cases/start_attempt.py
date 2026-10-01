"""Begin an attempt at an exercise: build the aggregate, provision the sandbox.

The first use case, and the one that establishes the shape the rest follow —
a frozen dataclass of ports with a `__call__`, so the composition root wires it
once and a route or a command invokes it like a function.

Two orderings in here are decisions rather than code layout.

**Gradability is checked before anything is built.** Provisioning a git scenario
runs its fixture, which creates a repository, bare remotes and a few dozen git
objects. Doing all that and only then discovering that nothing can grade the
result wastes the work and, worse, leaves a workspace on disk for an attempt
that can never be completed. The registry is asked first.

**The workspace is provisioned before the attempt is saved.** Both orders can
fail halfway and the asymmetry decides it: a workspace with no attempt row is
precisely what `practice gc` is built to find and collect (§8.1), while an
attempt row with no workspace is an active attempt the resume prompt will offer
and nothing can resume. So the recoverable leftover is the one to risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import StartedAttempt
from practice.application.errors import ExerciseNotFoundError
from practice.domain.attempt import Attempt, AttemptPolicy

if TYPE_CHECKING:
    from practice.application.registry import GraderRegistry
    from practice.domain.ids import ExerciseId
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        IdGenerator,
        SandboxProvisioner,
    )

__all__ = ["StartAttempt"]


@dataclass(frozen=True, slots=True)
class StartAttempt:
    """Provision a workspace for a fresh attempt and remember it."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    graders: GraderRegistry
    clock: Clock
    ids: IdGenerator

    def __call__(self, exercise_id: ExerciseId) -> StartedAttempt:
        exercise = self.content.get(exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(f"no exercise with id {exercise_id}")

        # Raises rather than returning, and deliberately before provisioning:
        # see the module docstring.
        self.graders.for_exercise(exercise)

        attempt_id = self.ids.new_attempt_id()
        attempt = Attempt(
            attempt_id=attempt_id,
            exercise_id=exercise.id,
            policy=AttemptPolicy.for_exercise(exercise),
            started_at=self.clock.now(),
        )

        workspace = self.provisioner.provision(exercise, attempt_id)
        self.attempts.save(attempt)

        return StartedAttempt(attempt=attempt, exercise=exercise, workspace=workspace)
