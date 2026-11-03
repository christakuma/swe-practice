"""Complete a half-typed console line against the attempt's own repository.

The rules live in `application/completion.py`, which is pure; this is the half
that has to touch something, and it touches the same things `InspectRepository`
does for the same reason. The branches a Tab offers are the branches the panel
beside the console draws, read through the `RepoQuery` the grader reads, so the
three cannot disagree about what exists.

**Read fresh on every press, not cached in the page.** A completion list that
was fetched when the page loaded would still offer `feature/webhooks` after the
solver deleted it, which in an exercise about a deleted branch is the one wrong
answer that matters. One `for-each-ref` and one `ls-files` per Tab is nothing
next to a person typing.

**A finished attempt completes nothing**, rather than raising: its workspace is
gone by design (§8.1), and a Tab key that produced an error would be louder
than the thing it was asked for. An active attempt with no workspace is still
`WorkspaceGoneError`, as everywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.application.completion import Completion, Vocabulary, complete
from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.exercise import GitScenarioSpec

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.ids import AttemptId, Sha
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        RepoQuery,
        RepoQueryFactory,
        SandboxProvisioner,
    )

__all__ = ["CompleteCommandLine"]

#: Full ref prefixes, and what the short name keeps. `refs/remotes/origin/main`
#: is typed `origin/main`, so only the namespace goes.
_SHORTENED: Final = ("refs/heads/", "refs/remotes/", "refs/tags/")

#: Revisions that are not refs but are typed as if they were. ORIG_HEAD is in
#: one exercise's title, so it is offered whether or not it exists yet.
_SYMBOLIC: Final = frozenset({"HEAD", "ORIG_HEAD"})


@dataclass(frozen=True, slots=True)
class CompleteCommandLine:
    """What a Tab press does to one line, in one attempt's repository."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    repo_query: RepoQueryFactory

    def __call__(self, attempt_id: AttemptId, line: str) -> Completion:
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
                f"{exercise.id} is a {exercise.kind.value} and has no console"
            )

        if not attempt.is_active:
            return Completion(line=line, matches=())

        workspace = self.provisioner.attach(exercise, attempt_id)
        if workspace is None:
            raise WorkspaceGoneError(
                f"the workspace for attempt {attempt.id.short} is no longer on "
                f"disk, so there is nothing to complete against"
            )

        return complete(
            line,
            vocabulary_of(self.repo_query(workspace), attempt.policy.allowed_commands),
        )


def vocabulary_of(repo: RepoQuery, programs: frozenset[str]) -> Vocabulary:
    """The words one repository offers, under the attempt's own allowlist.

    The attempt's rather than the exercise's, because the policy copied onto
    the attempt is what `RunScenarioCommand` enforces (§4.3), and a Tab should
    not offer a program the next Enter would refuse.
    """
    refs = repo.refs()
    return Vocabulary(
        programs=programs,
        revisions=_revisions(refs, repo.stash_list()),
        paths=repo.worktree_paths(),
        remotes=_remotes(refs),
    )


def _remotes(refs: Mapping[str, Sha]) -> frozenset[str]:
    """Read off remote-tracking refs, the only place `RepoQuery` shows them.

    A remote nothing has been fetched from yet has no refs and is not offered.
    Every remote in these fixtures has been pushed to, and a port method for
    `git remote` would be one call forwarded for one Tab.
    """
    return frozenset(
        name.removeprefix("refs/remotes/").split("/", 1)[0]
        for name in refs
        if name.startswith("refs/remotes/")
    )


def _revisions(refs: Mapping[str, Sha], stashes: Sequence[str]) -> frozenset[str]:
    names = set(_SYMBOLIC)
    for name in refs:
        for prefix in _SHORTENED:
            if name.startswith(prefix):
                names.add(name.removeprefix(prefix))
                break
    names.update(f"stash@{{{index}}}" for index in range(len(stashes)))
    return frozenset(names)
