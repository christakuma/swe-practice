"""Project one attempt into what its solver has already seen. Writes nothing.

The read behind "ask an AI about this": a workbench button, `practice context`
and the MCP server all hand a model the same thing, and this is where that thing
is decided. Phase 18; ADR 0023 has the alternatives.

**Nothing new is tracked, and that is the finding rather than a shortcut.** The
obvious design for "a record of what I did, to paste into a chat" is a recorder:
a second log, written as the solver works. `Attempt` has kept exactly that log
since Phase 1 -- every command with its output, every hint with its index --
because the process assertions and the grade suggestion read it. So this is a
*projection* of state the application already owns, and the only code it needed
was the choice of what to leave out.

**What it leaves out is the whole decision.** The use case reads an `Exercise`,
which holds every hint, the author's notes and a check list that all but states
the answer, and it copies across only what the solver has been shown:

* the hints the attempt *recorded* being revealed, never the list they came from;
* a count of the hints left, never their text;
* no check, no label, no explanation -- until a verdict exists, at which point
  the verdict page has already shown all three.

The alternative was to hand the model everything and tell it not to repeat the
answer. A prompt is a request, and the bundle is plain text the solver pastes by
hand and can read on the way; a boundary that depends on neither of those is the
one worth having. The reference solution was never reachable at all -- the
domain holds its *filename* (`exercise.py`), and no port a use case sees can
open it.

**It reads the repository through `view_of`**, the same function the repo state
panel is built from, so the tutor and the solver are looking at one reading of
one repository (ADR 0012's argument, a third time).

**An open attempt whose workspace is gone is still answered**, with no
repository. `InspectRepository` raises there, correctly -- a panel with nothing
to draw has to say so -- but the history is the larger half of this, it lives in
the database rather than the workspace, and "why did that rebase stop?" is as
askable after `practice gc` as before it. `RevealHint` makes the same call for
the same reason.

**An open interview is refused, and the rule is the policy's.** A model asked for
a nudge is a hint by another route (`AttemptPolicy.offers_tutor`). Only while it
is open: a finished interview is picked over like any other attempt, and that
half of the rule lives here because the policy does not know whether the attempt
it belongs to has ended.

**No clock, and no elapsed time in the result.** How long someone has been stuck
is not something a tutor needs to be told, and a use case that took a clock for
a display value would have stopped being a pure function of the attempt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import TutorContext
from practice.application.errors import AttemptNotFoundError, ExerciseNotFoundError
from practice.application.use_cases.inspect_repository import view_of
from practice.domain.attempt import SolutionSaved
from practice.domain.errors import PolicyViolationError
from practice.domain.exercise import GitScenarioSpec, editable_source

if TYPE_CHECKING:
    from practice.application.dto import RepoView
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import EditableSource, Exercise
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        RepoQueryFactory,
        SandboxProvisioner,
        Workspace,
    )

__all__ = ["ExportTutorContext"]


@dataclass(frozen=True, slots=True)
class ExportTutorContext:
    """Build the tutor context for one attempt. Read-only."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    repo_query: RepoQueryFactory

    def __call__(
        self, attempt_id: AttemptId, *, draft: str | None = None
    ) -> TutorContext:
        """`draft` is the solver's unsaved source, when the caller is holding it.

        The browser editor's contents exist nowhere else until they are
        submitted, so the workbench passes them in. A caller with nothing to
        pass gets the file in the workspace, which is the working copy in
        own-editor mode and the untouched stub otherwise.

        Raises `PolicyViolationError` for an interview that is still open.
        """
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library"
            )

        if attempt.is_active and not attempt.policy.offers_tutor:
            raise PolicyViolationError(
                "interview mode withholds the tutor until this attempt is finished"
            )

        workspace = (
            self.provisioner.attach(exercise, attempt_id) if attempt.is_active else None
        )
        editable = editable_source(exercise.spec)
        graded = attempt.verdict is not None

        return TutorContext(
            exercise_id=exercise.id,
            title=exercise.title,
            kind=exercise.kind,
            difficulty=exercise.difficulty,
            prompt=exercise.prompt,
            status=attempt.status,
            mode=attempt.policy.mode,
            allowed_commands=tuple(sorted(attempt.policy.allowed_commands)),
            commands_left=attempt.remaining_commands,
            hints_left=attempt.remaining_hints,
            events=tuple(
                event
                for event in attempt.events
                if not isinstance(event, SolutionSaved)
            ),
            repo=self._repo(exercise, workspace),
            source=_source(attempt, editable, workspace, draft),
            language=editable.language if editable is not None else None,
            verdict=attempt.verdict,
            # With the verdict or not at all: see `TutorContext`.
            notes=exercise.notes if graded else None,
        )

    def _repo(self, exercise: Exercise, workspace: Workspace | None) -> RepoView | None:
        """The live repository, for the one kind and the one state that has one."""
        if workspace is None or not isinstance(exercise.spec, GitScenarioSpec):
            return None
        return view_of(self.repo_query(workspace))


def _source(
    attempt: Attempt,
    editable: EditableSource | None,
    workspace: Workspace | None,
    draft: str | None,
) -> str | None:
    """The solver's answer as it stands, or `None` when there is no file to edit.

    Three places it can be, in the order they are trusted. A finished attempt's
    is the last one the log recorded, because that is the source the verdict
    beside it was computed from -- a `draft` offered for a graded attempt would
    be describing a different answer to the one that failed. An open attempt's
    is whatever the caller is holding, and failing that the file on disk.

    A missing or unreadable file is `None` rather than an error, which is the
    call `OpenWorkbench` makes about the same file: this is a description of an
    attempt, and the wrong place to find out a stub was never copied in.
    """
    if editable is None:
        return None
    if not attempt.is_active:
        saved = [event for event in attempt.events if isinstance(event, SolutionSaved)]
        return saved[-1].source if saved else None
    if draft is not None:
        return draft
    if workspace is None:
        return None
    try:
        return workspace.read_file(editable.filename)
    except OSError:
        return None
