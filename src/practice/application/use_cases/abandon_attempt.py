"""Give up on an attempt without grading it, and free its workspace.

The other half of the resume-or-abandon prompt PLAN.md §8.1 requires on startup. An
interrupted session must be neither silently lost nor silently resurrected, which
means there has to be a way to say *no* that is as explicit as resuming — and that
leaves the attempt in the log, marked, rather than deleting the row.

Three decisions.

**The row is saved before the workspace is deleted.** The same asymmetry
`StartAttempt` reasons about, from the other end: a workspace with no active attempt
is exactly what `practice gc` is built to collect, while a deleted workspace under
an attempt still marked `ACTIVE` is a session the resume prompt will keep offering
and nothing can ever resume. So the recoverable failure is the one to risk.

**It discards rather than attaching and disposing.** `Workspace.dispose` needs an
`Exercise` to attach with, and the single most important case for abandoning is the
one where the exercise is *gone* — renamed or deleted from the library under a live
attempt, leaving something that can never be graded. `SandboxProvisioner.discard`
takes the directory name, which is the only handle that survives that.

**It still looks the exercise up, and tolerates not finding it.** Only so the caller
can say which exercise was given up on; a missing one is reported as the id it
already has.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import Abandoned
from practice.application.errors import AttemptNotFoundError
from practice.domain.errors import AttemptStateError

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        SandboxProvisioner,
    )

__all__ = ["AbandonAttempt"]


@dataclass(frozen=True, slots=True)
class AbandonAttempt:
    """Mark an attempt abandoned and collect the workspace it was using."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    clock: Clock

    def __call__(self, attempt_id: AttemptId) -> Abandoned:
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
        if not attempt.is_active:
            # Refused rather than treated as idempotent. "Already abandoned" and
            # "already graded" are both things a user needs to be told, and the
            # second one especially: silently succeeding on a completed attempt
            # would let a mistyped id throw away a verdict's workspace.
            raise AttemptStateError(
                f"cannot abandon: attempt {attempt.id.short} is {attempt.status.value}"
            )

        attempt.abandon(at=self.clock.now())
        self.attempts.save(attempt)

        # Only now: the attempt is no longer active, so nothing owns the directory
        # and §8.1's rule that a workspace lives exactly as long as its attempt is
        # satisfied by deleting it.
        self.provisioner.discard(attempt_id.short)

        return Abandoned(
            attempt=attempt, exercise=self.content.get(attempt.exercise_id)
        )
