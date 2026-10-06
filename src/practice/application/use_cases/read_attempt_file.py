"""Read one file from an open attempt, for a tutor that asked to see it.

The second half of Phase 19's read side. `ExportTutorContext` says *which* paths
are unmerged; this is how a tutor looks at the conflict markers in one of them,
or at what a file held two commits ago. It exists for the MCP server and has no
other caller, which is worth saying because it is the first use case here that
a person never invokes: the one asking is a model, mid-conversation, choosing
its own arguments.

**That is the fact every decision in this module follows from.** Everything
else in `use_cases/` is handed arguments a solver typed or a template built.
This is handed a path and a revision by a program that has read the solver's
transcript and may have read anything else, so both are treated the way the
sandbox treats a typed command line: as untrusted input.

**Read-only by construction rather than by care.** The plan for this phase
sketched a tool that runs "read-only" git commands through the command policy,
and that was the wrong shape: whether `git branch` reads or writes depends on
its arguments, so the classification would have been a second, worse copy of
git's own option parser. `RepoQuery` is already the read-only port -- every
method on it is a question -- so a use case that reaches the repository only
through it cannot change one, whatever it is asked.

**With one exception that had to be closed here, and it is the finding.**
`GitRepoQuery.read_blob` runs `git show <rev>:<path>`. Every caller until now
passed a revision an exercise *author* wrote, which is trusted content (§8.1).
A revision beginning with `-` is an option to git, and `--output=FILE` makes
`git show` open one for writing -- run against real git to be sure, per ADR
0022, and it does. So "read-only port" was true of the port's contract and not
of its implementation the moment the revision came from somewhere else.
Two guards, because they fail differently: a revision starting with `-` is
refused outright, and what reaches `read_blob` is never the caller's string
at all but the hash `rev_parse` resolved it to, which is forty hex characters
and cannot be mistaken for anything.

**A kata's hidden suite is refused, and refused rather than reported
missing.** `tests.py` is in the workspace beside the stub, because pytest has
to run it from there (ADR 0020 spends its longest section on why). The one
file a tutor may read from a kata or a drill is the one the solver edits, plus
a drill's `seed.sql`, which the solver is meant to read. Answering "no such
file" for the suite would be a lie a model could catch by listing the
directory some other way; the refusal names what *can* be read instead.

**`None` means the file is not there**, which for a repository in the middle of
being repaired is an ordinary answer and not a fault -- the same call
`RepoQuery` makes about a ref that does not resolve.

**Only an open attempt.** A finished one has no workspace (§8.1), and its
history is already in the context. An open interview is refused through the
policy, exactly as the context is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    UnsupportedExerciseKindError,
    WorkspaceGoneError,
)
from practice.domain.errors import (
    AttemptStateError,
    InvalidValueError,
    PolicyViolationError,
)
from practice.domain.exercise import GitScenarioSpec, SqlDrillSpec, editable_source

if TYPE_CHECKING:
    from practice.domain.exercise import Exercise
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        ContentRepository,
        RepoQuery,
        RepoQueryFactory,
        SandboxProvisioner,
        Workspace,
    )

__all__ = ["ReadAttemptFile"]


@dataclass(frozen=True, slots=True)
class ReadAttemptFile:
    """Read one file from an attempt's workspace. Writes nothing."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    repo_query: RepoQueryFactory

    def __call__(
        self, attempt_id: AttemptId, path: str, *, rev: str | None = None
    ) -> str | None:
        """The file's text, or `None` when there is no such file.

        `rev` reads the committed copy at a revision instead of the working
        tree's, and only a git scenario has one.
        """
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
        if not attempt.is_active:
            raise AttemptStateError(
                f"cannot read a file: attempt {attempt.id.short} is "
                f"{attempt.status.value}, and its workspace went with it"
            )

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library"
            )

        if not attempt.policy.offers_tutor:
            raise PolicyViolationError(
                "interview mode withholds the tutor until this attempt is finished"
            )

        workspace = self.provisioner.attach(exercise, attempt_id)
        if workspace is None:
            raise WorkspaceGoneError(
                f"the workspace for attempt {attempt.id.short} is no longer on "
                f"disk, so there is no file to read"
            )

        if isinstance(exercise.spec, GitScenarioSpec):
            return _from_repository(self.repo_query(workspace), path, rev)
        return _from_directory(exercise, workspace, path, rev)


def _from_repository(repo: RepoQuery, path: str, rev: str | None) -> str | None:
    """A scenario's file: the working tree's copy, or a committed one.

    See the module docstring for why the revision is resolved before it is
    used. A revision that does not resolve is `None`, like a file that is not
    there: both mean there is nothing at that address, and a tutor that asked
    for `HEAD~9` in a three-commit repository has been answered.
    """
    if rev is None:
        return repo.worktree_file(path)
    if rev.startswith("-"):
        raise InvalidValueError(
            f"{rev!r} is not a revision: one cannot begin with a hyphen"
        )
    sha = repo.rev_parse(rev)
    if sha is None:
        return None
    blob = repo.read_blob(sha.value, path)
    # `replace` rather than `strict`: a solver can commit any bytes they like,
    # and a file that will not decode should read as noise, not raise.
    return None if blob is None else blob.decode("utf-8", errors="replace")


def _from_directory(
    exercise: Exercise, workspace: Workspace, path: str, rev: str | None
) -> str | None:
    """A kata's or a drill's file, which is one of a short list or a refusal."""
    readable = _readable(exercise)
    if rev is not None:
        raise UnsupportedExerciseKindError(
            f"{exercise.id} is a {exercise.kind.value} and has no repository, so "
            f"there is no revision to read a file at"
        )
    if path not in readable:
        raise UnsupportedExerciseKindError(
            f"{exercise.id} is a {exercise.kind.value}: a tutor may read "
            f"{' and '.join(readable)} from its workspace and nothing else"
        )
    try:
        return workspace.read_file(path)
    except OSError:
        return None


def _readable(exercise: Exercise) -> tuple[str, ...]:
    """The files in a non-repository workspace that a solver is meant to read.

    The one they edit, and for a drill the seed that builds its database --
    which `SqlDrillSpec` says the solver is *meant* to read, because the schema
    is the question. Not the hidden suite and not the reference, neither of
    which `editable_source` names.
    """
    spec = exercise.spec
    source = editable_source(spec)
    names = [source.filename] if source is not None else []
    if isinstance(spec, SqlDrillSpec):
        names.append(spec.seed)
    return tuple(names)
