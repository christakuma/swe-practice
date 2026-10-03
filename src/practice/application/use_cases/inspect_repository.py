"""Read an attempt's repository for display. Writes nothing, grades nothing.

**It reads through the same port the grader reads through, and that is the whole
decision in this module.** The repo state panel could have been built on a second
git-parsing path written for display — `git status` as humans see it, `git branch`
in colour — and it would have been less code on day one. It would also have meant
two answers to *is this worktree clean?* in one application: the one the verdict is
derived from, and the one the solver is looking at while they decide whether to
submit. A panel that disagrees with the grader is worse than no panel, because the
solver cannot tell which of the two lied.

So inspection goes through `RepoQuery` — the port the 22 assertions are pure
functions over — and the panel is, structurally, the same reading of the repository
that will grade it a moment later.

**One `RepoQuery` per call, built from the factory.** `GitRepoQuery` caches for the
life of the instance, which is what makes six questions cost one `git` process; the
cache is only safe because the instance does not outlive the request. An instance
held across a solver's commands would redraw the panel with the repository as it was
*before* the command that prompted the redraw — the one bug a cache in this position
can have, and a silent one.

**A finished attempt has no repository, and that is `None` rather than an error.**
Submission disposes of the workspace (§8.1 ties its lifetime to `ACTIVE`), so a tab
left open across a submission asks for a panel there is nothing to draw — the same
shape `OpenWorkbench` already handles, and the same answer. A *still active* attempt
with no workspace is `WorkspaceGoneError`, exactly as it is everywhere else.

**A kata is refused rather than inspected.** Its workspace is a directory with a
stub in it and no repository at all, so every field would come back empty and the
panel would read as a repository in a strange state rather than as a question that
does not apply. `RunScenarioCommand` refuses the same thing for the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import RepoView
from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.exercise import GitScenarioSpec

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.ids import AttemptId, Sha
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        RepoQuery,
        RepoQueryFactory,
        SandboxProvisioner,
    )

__all__ = ["InspectRepository"]

#: Where a ref of each kind lives. Full names, because that is what `refs()`
#: answers with and what the assertions read; the panel shortens them for display
#: and `RepoView` owns that half.
_HEADS = "refs/heads/"
_REMOTES = "refs/remotes/"
_TAGS = "refs/tags/"


@dataclass(frozen=True, slots=True)
class InspectRepository:
    """Load one attempt's repository state. Read-only, and read through the port."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    repo_query: RepoQueryFactory

    def __call__(self, attempt_id: AttemptId) -> RepoView | None:
        """`None` for a finished attempt, whose workspace is gone by design."""
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library"
            )
        if not isinstance(exercise.spec, GitScenarioSpec):
            raise ExerciseNotFoundError(
                f"{exercise.id} is a {exercise.kind.value} and has no repository to "
                f"inspect"
            )

        if not attempt.is_active:
            return None

        workspace = self.provisioner.attach(exercise, attempt_id)
        if workspace is None:
            raise WorkspaceGoneError(
                f"the workspace for attempt {attempt.id.short} is no longer on "
                f"disk, so there is nothing to inspect; abandon it and start again"
            )

        return _view(self.repo_query(workspace))


def _view(repo: RepoQuery) -> RepoView:
    """Six questions, asked once each, through one cached query instance.

    `refs()` is asked once and split three ways rather than asked three times,
    which matters because the real implementation caches per instance and a reader
    should not have to know that to see why this is cheap.
    """
    refs = repo.refs()
    return RepoView(
        head_ref=repo.head_ref(),
        head_sha=repo.rev_parse("HEAD"),
        status=repo.status(),
        branches=_under(refs, _HEADS),
        remote_branches=_under(refs, _REMOTES),
        tags=_under(refs, _TAGS),
        stashes=repo.stash_list(),
    )


def _under(refs: Mapping[str, Sha], prefix: str) -> dict[str, Sha]:
    """The refs of one kind, keyed by their full names and in a stable order.

    Sorted, because `refs()` makes no promise about order and a panel whose
    branches reshuffle between two commands is a panel nobody can read a change
    out of — which is the one thing this panel exists to let someone do.
    """
    return {name: sha for name, sha in sorted(refs.items()) if name.startswith(prefix)}
