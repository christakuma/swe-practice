"""Everything a workbench page needs about one attempt, in whatever state it is in.

**The first use case the CLI never needed, and the reason is structural rather
than cosmetic: a URL outlives the state it was created for.** `practice submit`
grades an attempt and prints a verdict, and the attempt is then finished and
nobody asks about it again. `/attempt/{id}` is a tab that is still open, a
bookmark, a link from the dashboard — and it has to render for an attempt that
was submitted thirty seconds ago as well as for one still being worked on.

`ResumeAttempt` cannot do it, and should not be bent into doing it. Resuming
means *give me the live session*, and it refuses a finished attempt with a
message saying so — which is right, because resuming one is not a thing that can
happen. This asks a different question: *render the page for this attempt*. The
two overlap on the happy path and diverge on exactly the case that forced this
module to exist.

**The workspace is `None` for a finished attempt, not an error.** Submission
disposes of it (§8.1 ties workspace lifetime to `ACTIVE`), so "gone" is the
expected state rather than the broken one, and a page that raised on it could
never show a verdict. For an attempt that is *still* active, a missing workspace
is `WorkspaceGoneError` exactly as it is in `ResumeAttempt`: that attempt can be
abandoned and never graded, and saying so is the only honest page.

**The editor seed comes from the workspace, not from the library.** The stub is
copied into the workspace when the attempt is provisioned, so reading it there
reads what this attempt actually started from — a library edited since would
otherwise silently reseed an open attempt with different code. It is also the
only place the application layer can read it from: `ContentRepository` hands back
an `Exercise` whose `KataSpec.stub` is a *filename*, and resolving that against a
content directory would put a path join in a layer that has no filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import Workbench
from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.exercise import KataSpec

if TYPE_CHECKING:
    from practice.domain.exercise import Exercise, ExerciseSpec
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        SandboxProvisioner,
        Workspace,
    )

__all__ = ["OpenWorkbench"]


@dataclass(frozen=True, slots=True)
class OpenWorkbench:
    """Load one attempt for display. Writes nothing."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner

    def __call__(self, attempt_id: AttemptId) -> Workbench:
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            # Same message as `ResumeAttempt`'s, because it is the same situation
            # and the same remedy: the library changed under a live attempt, and
            # the only thing that can still be done with it is abandon it.
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library; abandon it"
            )

        workspace = self._workspace(exercise, attempt_id) if attempt.is_active else None
        return Workbench(
            attempt=attempt,
            exercise=exercise,
            workspace=workspace,
            editor_source=_seed(exercise.spec, workspace),
        )

    def _workspace(self, exercise: Exercise, attempt_id: AttemptId) -> Workspace:
        """The live workspace, or the refusal that says the attempt is stranded."""
        workspace = self.provisioner.attach(exercise, attempt_id)
        if workspace is None:
            raise WorkspaceGoneError(
                f"the workspace for attempt {attempt_id} is no longer on disk, so "
                f"there is nothing to work in; abandon it and start again"
            )
        return workspace


def _seed(spec: ExerciseSpec, workspace: Workspace | None) -> str | None:
    """What the editor opens with, or `None` when there is no editor.

    `None` rather than an empty string, and the distinction is one the template
    reads: a git scenario has no editor at all (its surface is a console, which is
    Phase 8), while a kata with an empty stub would have one that happens to be
    blank. A missing stub file is also `None` rather than an exception -- the
    content suite is what holds a kata to having one, and a workbench that refused
    to load would be the wrong place to find out.
    """
    if workspace is None or not isinstance(spec, KataSpec):
        return None
    try:
        return workspace.read_file(spec.stub)
    except OSError:
        return None
