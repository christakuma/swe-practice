"""Hand the attempt's solution file to the solver's own editor.

The first half of own-editor mode (PLAN.md §11, Phase 10). The premise is that
some people think better in their own editor than in a textarea, and the
workspace already contains the file they would want: `SandboxProvisioner` copies
a kata's stub into `<workspace>/repo/<stub>` when the attempt is provisioned.

**So there is nothing to scaffold, and finding that out is the point.** The
first draft of this phase created a second file — `work.py`, say — for the
solver to edit. That is one file too many: `OpenWorkbench` already seeds the
browser editor by reading `spec.stub` out of the workspace, so a second file
would have made the page and the editor show different things, and whichever one
was submitted the other would have been silently discarded. The stub *is* the
working copy, and has been since Phase 3. What was missing was its path.

**The optional `source` is the handoff, and it is not an event.** Someone who
typed into the browser editor and then decided to switch must not lose it, so
the page sends what is on screen and it is written to the file before the editor
opens on it. Nothing is appended to the attempt's log: Phase 8 settled that an
editor save is a keystroke rather than something the solver *did in the
exercise* (§16), and a log full of them would make every §6.3 process assertion
learn to ignore a kind of entry. The file is the state; the log is the story.

**A git scenario is refused rather than given an empty answer**, which is the
mirror of `InspectRepository` refusing a kata. A scenario's surface is a console
over a repository and there is no file to open — the repository is already on
disk, and `cd` is the whole of "work on it in your own tools".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import RevealedFile
from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    UnsupportedExerciseKindError,
    WorkspaceGoneError,
)
from practice.domain.errors import AttemptStateError
from practice.domain.exercise import editable_source

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        EditorLauncher,
        SandboxProvisioner,
        Workspace,
    )

__all__ = ["RevealSolutionFile", "SolutionFile", "load_solution_file"]


@dataclass(frozen=True, slots=True)
class SolutionFile:
    """One attempt's editable file, resolved: the attempt, the exercise, the live
    workspace and the absolute path.

    Not a DTO — it holds a live `Workspace`, so it never leaves this layer. It
    exists because two use cases need all four and must agree about every way
    finding them can fail: this one reveals the file and `WatchSolutionFile`
    grades it on every save, and a page that offered the first on attempts the
    second refuses would be a page with a button that does nothing. Shared the
    way `OfferReview` and `GradeReview` share `load_offer`, and for the same
    reason.
    """

    attempt: Attempt
    exercise: Exercise
    workspace: Workspace
    path: Path
    #: The repository-relative name, which is what `Workspace` reads and writes
    #: by. Carried alongside the absolute path rather than derived from it:
    #: deriving it means knowing where the repository root is, and that is the
    #: workspace's business and not this layer's.
    relative: str


def load_solution_file(
    attempt_id: AttemptId,
    *,
    content: ContentRepository,
    attempts: AttemptRepository,
    provisioner: SandboxProvisioner,
) -> SolutionFile:
    """Find the attempt, its exercise, its live workspace and its file.

    Every refusal here is one of the four `OpenWorkbench` already has, with the
    same sentences, plus two this question adds: an attempt that is finished has
    no workspace to edit in, and an exercise with no editable file cannot have
    one revealed.
    """
    attempt = attempts.get(attempt_id)
    if attempt is None:
        raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
    if not attempt.is_active:
        raise AttemptStateError(
            f"cannot work on a file: attempt {attempt.id.short} is "
            f"{attempt.status.value}"
        )

    exercise = content.get(attempt.exercise_id)
    if exercise is None:
        raise ExerciseNotFoundError(
            f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
            f"no longer in the library; abandon it"
        )

    source = editable_source(exercise.spec)
    if source is None:
        raise UnsupportedExerciseKindError(
            f"{exercise.id} is a {exercise.kind.value}: it is graded on the "
            f"repository in its workspace, so there is no solution file to open"
        )

    workspace = provisioner.attach(exercise, attempt_id)
    if workspace is None:
        raise WorkspaceGoneError(
            f"the workspace for attempt {attempt.id.short} is no longer on disk, "
            f"so there is no file to open; abandon it and start again"
        )

    return SolutionFile(
        attempt=attempt,
        exercise=exercise,
        workspace=workspace,
        path=workspace.resolve(source.filename),
        relative=source.filename,
    )


@dataclass(frozen=True, slots=True)
class RevealSolutionFile:
    """Put the attempt's solution file in front of the solver.

    No clock and no graders: writing the handoff records nothing and grades
    nothing. The `EditorLauncher` is the one port here no other use case holds.
    """

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    editor: EditorLauncher

    def __call__(
        self, attempt_id: AttemptId, source: str | None = None
    ) -> RevealedFile:
        found = load_solution_file(
            attempt_id,
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
        )

        # Write before launching, so the editor opens on the handoff rather than
        # on what was there a moment ago. An editor that reloads a file changed
        # underneath it is a well-behaved editor; one that is asked to open a
        # file and shows the previous bytes is a bug nobody can reproduce.
        if source is not None:
            found.workspace.write_file(found.relative, source)

        problem = self.editor.reveal(found.path)
        return RevealedFile(
            attempt=found.attempt,
            exercise=found.exercise,
            path=found.path,
            launched=problem is None,
            detail=problem,
        )
