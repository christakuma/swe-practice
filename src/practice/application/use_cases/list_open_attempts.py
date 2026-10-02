"""What the resume-or-abandon prompt is a prompt about.

Every attempt still `ACTIVE`, each joined to its exercise and to whether its
workspace is still on disk. That third fact is the one that makes the list useful
rather than merely true: an attempt whose workspace has been collected can be
abandoned and never resumed, and offering both choices for it would offer one that
cannot be taken.

**The join is here rather than in the caller.** An `Attempt` holds an `ExerciseId`,
not an `Exercise`, so rendering anything at all means another trip to the content
repository — and doing it per caller is how a CLI command and a web route end up
disagreeing about what to do when the exercise has been deleted (`dto.py`). The
answer they share is: show the id, and let it be abandoned.

**Membership is tested on `short_id`, not on the metadata.** The workspace directory
is named after the attempt's short id (PLAN.md §8.1), so the question "is this
attempt's workspace there?" is answerable from the directory name alone — which
matters because the leftover of an interrupted provision has no readable metadata
and would otherwise look like no workspace at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import OpenAttempt

if TYPE_CHECKING:
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        SandboxProvisioner,
    )

__all__ = ["ListOpenAttempts"]


@dataclass(frozen=True, slots=True)
class ListOpenAttempts:
    """Every attempt that has been neither submitted nor abandoned."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner

    def __call__(self) -> tuple[OpenAttempt, ...]:
        """Oldest first, which is the repository's order rather than a choice here.

        One listing of the workspace root for the whole set rather than one `attach`
        per attempt: the question is about directory names, and attaching would run
        the command policy and read a gitconfig to answer it.
        """
        on_disk = {found.short_id for found in self.provisioner.workspaces()}
        return tuple(
            OpenAttempt(
                attempt=attempt,
                exercise=self.content.get(attempt.exercise_id),
                workspace_on_disk=attempt.id.short in on_disk,
            )
            for attempt in self.attempts.active()
        )
