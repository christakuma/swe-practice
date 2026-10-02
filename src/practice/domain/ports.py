"""Every port in the system, as `typing.Protocol`.

Protocols rather than ABCs, and the reason is structural typing: an adapter
implements a port without importing it and without an inheritance relationship
pointing the wrong way, and a fake needs no base class — `FakeClock` is five
lines (ADR 0002).

The port's own data vocabulary lives here too — `WorktreeStatus`, `ReflogEntry`,
`CommitInfo`. They are pure value objects describing git state, and keeping them
next to the protocol that returns them means `GitRepoQuery` and `FakeRepoQuery`
cannot disagree about their shape, which is the drift that stops a fake being
evidence of anything.

Per PLAN.md §13, every port has to earn its keep with at least two real or test
implementations. `RepoQuery` earns it on day one. Where a port ends up with one
implementation and no test double, the honest response is to delete it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import date, datetime

    from practice.domain.attempt import Attempt, CommandResult
    from practice.domain.exercise import Exercise, ExerciseFilter
    from practice.domain.ids import AttemptId, ExerciseId, Sha
    from practice.domain.review import Grade, ReviewCard
    from practice.domain.verdict import Verdict

__all__ = [
    "AttemptRepository",
    "Clock",
    "CommitInfo",
    "ContentRepository",
    "Grader",
    "IdGenerator",
    "ReflogEntry",
    "RepoQuery",
    "ReviewRepository",
    "SandboxProvisioner",
    "Scheduler",
    "Workspace",
    "WorktreeStatus",
]


# --- the RepoQuery vocabulary ---------------------------------------------


@dataclass(frozen=True, slots=True)
class WorktreeStatus:
    """A porcelain status, split by the four states an assertion cares about.

    Paths are repository-relative and forward-slashed, whatever the platform.
    """

    staged: frozenset[str] = frozenset()
    unstaged: frozenset[str] = frozenset()
    untracked: frozenset[str] = frozenset()
    unmerged: frozenset[str] = frozenset()

    @property
    def is_clean(self) -> bool:
        """Clean by `worktree_clean`'s default: untracked files are ignored.

        A scratch file someone created while poking around should not fail them
        (PLAN.md §6.5). The default lives here rather than in the assertion so that
        both `RepoQuery` implementations answer the question the same way.
        """
        return not (self.staged or self.unstaged or self.unmerged)

    @property
    def is_pristine(self) -> bool:
        """Clean including untracked — `worktree_clean {include_untracked: true}`."""
        return self.is_clean and not self.untracked


@dataclass(frozen=True, slots=True)
class ReflogEntry:
    """One position a ref has held. `index` is the `n` in `HEAD@{n}`."""

    index: int
    sha: Sha
    message: str


@dataclass(frozen=True, slots=True)
class CommitInfo:
    """A commit, in the fields the assertions actually read.

    `parents` is here because `linear_history` needs to know a merge when it sees
    one, and `tree` because `tree_equals` compares committed content rather than
    commit identity.
    """

    sha: Sha
    tree: Sha
    subject: str
    parents: tuple[Sha, ...] = ()

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


# --- content, attempts, reviews -------------------------------------------


class ContentRepository(Protocol):
    """Read-only access to the exercise library on disk."""

    def list_exercises(
        self, criteria: ExerciseFilter | None = None
    ) -> Sequence[Exercise]: ...

    def get(self, exercise_id: ExerciseId) -> Exercise | None: ...


class AttemptRepository(Protocol):
    """Persistence for attempts, including their full event log."""

    def save(self, attempt: Attempt) -> None: ...

    def get(self, attempt_id: AttemptId) -> Attempt | None: ...

    def history_for(self, exercise_id: ExerciseId) -> Sequence[Attempt]: ...

    def active(self) -> Sequence[Attempt]:
        """Every attempt that has been neither submitted nor abandoned.

        Added in Phase 6, and it is the method the whole attempt table was for.
        PLAN.md §8.1 defines the lifecycle as active until submitted *or*
        abandoned, ties the workspace's lifetime to exactly that, and defines an
        orphan as a workspace with no active attempt row — so without a way to
        ask the question, `practice gc` can see the workspaces and not which of
        them are still in use, and the resume prompt has nothing to offer.

        A query on the port rather than a filter over `history_for` across every
        exercise, because the answer is a single indexed lookup and the
        alternative is loading the entire history to throw almost all of it away.
        """
        ...


class ReviewRepository(Protocol):
    """Persistence for scheduling state."""

    def get_card(self, exercise_id: ExerciseId) -> ReviewCard | None: ...

    def save_card(self, card: ReviewCard) -> None: ...

    def due_on(self, day: date) -> Sequence[ReviewCard]: ...


# --- the sandbox ----------------------------------------------------------


class Workspace(Protocol):
    """A provisioned directory an attempt runs inside.

    `run` takes an argv list, never a command string: user input gets no shell, so
    there is nothing for a shell to reinterpret (PLAN.md §8.1). Policy — the
    allowlist and the metacharacter rejection — is applied before anything reaches
    here.

    **`run` and `run_tool` are the two halves of the trust split** PLAN.md §8.1
    rests on, in the one place a grader can see both. `run` is untrusted input:
    whatever the solver typed, under the exercise's allowlist. `run_tool` is
    trusted code: an argv a grading engine built for itself — the kata engine's
    `python -m pytest`, the Phase 5 `git` interrogation — which no allowlist
    could usefully gate, because the exercise author never wrote it down. A
    grader that put user input through `run_tool` would have defeated the
    policy, which is why the split is named here rather than left implicit.
    """

    def run(self, argv: Sequence[str], timeout: float) -> CommandResult: ...

    def run_tool(self, argv: Sequence[str], timeout: float) -> CommandResult: ...

    def read_file(self, path: str) -> str: ...

    def write_file(self, path: str, content: str) -> None: ...

    def aliases(self) -> Mapping[str, Sha]:
        """The fixture's `@c1`-style symbolic names, as it recorded them.

        Here rather than only on the concrete workspace because a `RepoQuery` is
        built *over* a workspace and needs them, and `Grader.grade` is handed the
        port. They live outside the repository on purpose (§6.1), so `read_file`
        — which confines itself to the repository — cannot reach them. Phase 5
        finding, recorded in PLAN.md §16.
        """
        ...

    def snapshot(self) -> Mapping[str, Sha]:
        """Every ref as it stood when the fixture finished, for `ref_unchanged`."""
        ...

    def dispose(self) -> None: ...


class SandboxProvisioner(Protocol):
    """Builds the workspace for an exercise and runs its fixture.

    `provision` takes the `AttemptId` because the workspace directory is named
    after the attempt (§8.1). The alternative is for the provisioner to generate
    identity, which means the `Attempt` aggregate learns its own id from its
    workspace and the `IdGenerator` port is injected in two places to produce one
    id (PLAN.md §16).

    `attach` returns `None` rather than raising when there is nothing on disk: an
    attempt whose workspace has been collected is a normal thing for a caller to
    decide about, not a fault.
    """

    def provision(self, exercise: Exercise, attempt_id: AttemptId) -> Workspace: ...

    def attach(self, exercise: Exercise, attempt_id: AttemptId) -> Workspace | None: ...


class RepoQuery(Protocol):
    """Read-only git interrogation. The port that makes the check engine pure.

    Every assertion depends on this rather than on a git process, which is what
    lets all 22 of them be unit-tested in milliseconds against an in-memory fake
    with no git installed and no filesystem touched (PLAN.md §6.2).

    Every lookup returns `None` rather than raising when a revision does not
    resolve. A missing ref is a clean assertion failure, never an error: half the
    point of these exercises is that the repository may be in a state nobody
    anticipated, and a traceback in the verdict panel teaches nothing (§6.5).
    """

    def rev_parse(self, rev: str) -> Sha | None: ...

    def tree_sha(self, rev: str) -> Sha | None: ...

    def is_ancestor(self, ancestor: Sha, descendant: Sha) -> bool: ...

    def subject(self, rev: str) -> str | None: ...

    def refs(self) -> Mapping[str, Sha]: ...

    def head_ref(self) -> str | None:
        """The ref `HEAD` is attached to, or `None` when it is detached.

        Added in Phase 5, because `head_detached` cannot be answered without it:
        `rev_parse("HEAD")` returns a hash whether HEAD is on a branch or not, and
        "no branch points at this commit" is a different question with a different
        answer (PLAN.md §16).
        """
        ...

    def status(self) -> WorktreeStatus: ...

    def reflog(self, ref: str) -> Sequence[ReflogEntry]: ...

    def log(self, rev: str) -> Sequence[CommitInfo]: ...

    def stash_list(self) -> Sequence[str]: ...

    def read_blob(self, rev: str, path: str) -> bytes | None: ...

    def worktree_file(self, path: str) -> str | None:
        """The working tree's copy of `path`, or `None` if it is not readable.

        Also added in Phase 5. Without it `file_exists` and `file_matches` could
        only ask about committed content, which is what `file_at_ref_matches`
        already does — and nothing could grade a state that has not been committed
        yet, which is exactly what a merge-conflict exercise ends in (§15).

        Text rather than bytes: every file these exercises touch is text, the
        assertions over it are regular expressions, and a file that will not decode
        reads as `None` rather than as noise a pattern might match.
        """
        ...

    def aliases(self) -> Mapping[str, Sha]:
        """The fixture's `@c1`-style symbolic names, resolved before git sees them."""
        ...

    def snapshot(self) -> Mapping[str, Sha]:
        """Every ref as it stood when the fixture finished, for `ref_unchanged`."""
        ...


# --- grading and scheduling -----------------------------------------------


class Grader(Protocol):
    """Turns a finished workspace into a verdict.

    One implementation per exercise kind, selected through the application's kind
    registry, which is why this is a port and not a function on `Exercise`.
    """

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict: ...


class Scheduler(Protocol):
    """Moves a review card after an attempt. SM-2 in v1, FSRS behind the same port."""

    def next_card(self, card: ReviewCard, grade: Grade, today: date) -> ReviewCard: ...


# --- ambient ---------------------------------------------------------------


class Clock(Protocol):
    """Time as a dependency.

    Looks like over-engineering until the first test that needs a deterministic due
    date, and retrofitting it is miserable, so it is injected from day one.
    `now()` is always timezone-aware — `Attempt` rejects anything else.
    """

    def now(self) -> datetime: ...

    def today(self) -> date: ...


class IdGenerator(Protocol):
    """Identity as a dependency, for the same reason as `Clock`: stable snapshots."""

    def new_attempt_id(self) -> AttemptId: ...
