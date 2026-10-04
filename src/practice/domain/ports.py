"""Every port in the system, as `typing.Protocol`.

Protocols rather than ABCs, and the reason is structural typing: an adapter
implements a port without importing it and without an inheritance relationship
pointing the wrong way, and a fake needs no base class — `FakeClock` is five
lines (ADR 0002).

The port's own data vocabulary lives here too — `WorktreeStatus`, `CommitInfo`
and `ResultSet`. They are pure value objects describing the state a grading
assertion reads, and keeping them next to the protocol that returns them means a
real adapter and its fake cannot disagree about their shape, which is the drift
that stops a fake being evidence of anything.

Per PLAN.md §13, every port has to earn its keep with at least two real or test
implementations. `RepoQuery` earns it on day one. Where a port ends up with one
implementation and no test double, the honest response is to delete it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping, Sequence
    from datetime import date, datetime
    from pathlib import Path

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
    "DrillQuery",
    "EditorLauncher",
    "FileWatcher",
    "Grader",
    "IdGenerator",
    "RepoQuery",
    "RepoQueryFactory",
    "ResultSet",
    "ReviewRepository",
    "SandboxProvisioner",
    "Scalar",
    "Scheduler",
    "Workspace",
    "WorkspaceSummary",
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
class WorkspaceSummary:
    """One workspace directory, as the provisioner found it on disk.

    Port vocabulary rather than an adapter type, because `practice gc`'s whole job
    is a *decision* over these — a workspace with no active attempt row is an
    orphan (PLAN.md §8.1) — and that decision belongs in a use case that can be
    unit-tested against a fake, not in a CLI command nobody can hold to it.

    **`short_id` is the handle, not `attempt_id`.** The directory name *is* the
    attempt's short id, so the orphan rule can be decided from the name alone —
    which matters because the most interesting leftover is an interrupted
    provision whose metadata was never written, and which therefore has no
    `attempt_id` to match on. Those fields describe a workspace; `short_id`
    identifies it.

    `size_bytes` is read eagerly rather than offered as a method, because the only
    caller wants it for every workspace it lists, and a lazily-computed size on a
    port would be an I/O call hiding behind an attribute access.
    """

    short_id: str
    attempt_id: AttemptId | None = None
    exercise_id: ExerciseId | None = None
    created_at: str | None = None
    size_bytes: int = 0

    @property
    def is_described(self) -> bool:
        """Whether the metadata file could be read.

        A workspace with none is still a workspace and gc has to report it: an
        interrupted provision is exactly the kind of leftover it exists to find.
        """
        return self.attempt_id is not None


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


# --- the DrillQuery vocabulary --------------------------------------------


#: Every type SQLite hands back from a cursor. Deliberately the real set rather
#: than `str`: a port that stringified on the way out would be deciding grading
#: policy, and how `NULL` compares to an author's expected value is a *domain*
#: question (`domain/drills/evaluation.as_text`) rather than a driver detail.
type Scalar = str | int | float | bytes | None


@dataclass(frozen=True, slots=True)
class ResultSet:
    """Column names and rows, as a cursor produced them.

    The shape both halves of a drill are read through: the rows an answer
    *returned*, and the rows a table was *left holding*. One type for both,
    because every assertion that can compare a result set can compare a table —
    `result_matches` and `table_matches` differ in where the rows came from and
    in nothing else.

    `rows` is a tuple of tuples rather than a tuple of mappings. A SQL result is
    positional, two columns can share a name (`SELECT a.id, b.id`), and an
    assertion about *column order* could not be written over a mapping at all.
    """

    columns: tuple[str, ...] = ()
    rows: tuple[tuple[Scalar, ...], ...] = ()

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def column(self, name: str) -> tuple[Scalar, ...] | None:
        """One column's values top to bottom, or `None` if there is no such column.

        `None` rather than a raise, for the reason the whole grading layer gives:
        an assertion naming a column the answer did not select is a clean failure
        a solver can act on, and a traceback is not (PLAN.md §6.5). The *first*
        column of that name, which is the same rule SQLite's own row access uses.
        """
        if name not in self.columns:
            return None
        index = self.columns.index(name)
        return tuple(row[index] for row in self.rows)


class DrillQuery(Protocol):
    """Read-only interrogation of a finished SQL drill. `RepoQuery`'s counterpart.

    The port that makes the drill assertions pure, and it is deliberately the
    same shape of thing as `RepoQuery`: an answer has already been run against a
    seeded database by the time anything here is called, and every method is a
    question about the state that run left behind. All ten assertions in
    `domain/drills/` are pure functions of one of these, so they are unit-tested
    against an in-memory fake with no SQLite file touched.

    **It covers both halves of what a drill grades**, which is the whole reason
    it is one port rather than two. `result` is what the answer *returned* — the
    half a `SELECT` drill is about. `table` and `tables` are what the database
    was *left holding* — the half an `INSERT`, `UPDATE`, `DELETE` or `CREATE`
    drill is about, and the half that is the project's core bet applied to SQL:
    grade the end state, not the text of the statement that produced it.

    `error` is how a drill says the answer did not run, and like `RepoQuery`'s
    `None` returns it is reported rather than raised. A syntax error is the most
    ordinary thing a solver does, and it has to arrive as a failing check with
    the message in it.
    """

    def error(self) -> str | None:
        """Why the answer did not run, or `None` if it did.

        A string and not an exception: SQLite's own message is the single most
        useful thing a solver can be shown — `near "FORM": syntax error` ends the
        problem where a traceback would start one.
        """
        ...

    def result(self) -> ResultSet | None:
        """What the answer's final row-returning statement produced.

        **The final one, not the only one.** An answer may legitimately be
        several statements — a `CREATE TEMP VIEW` then a `SELECT` over it, or a
        `DELETE` then a `SELECT` showing what is left — and the one being graded
        is the one at the end. `None` means the answer returned no rows at all,
        which is the normal case for a drill graded purely on `table`.
        """
        ...

    def table(self, name: str) -> ResultSet | None:
        """Every row of one table as the answer left it, or `None` if it is gone.

        Column order is the table's declared order and row order is `rowid`, so
        the result is stable enough to compare against an author's literal rows
        without the drill having to specify an `ORDER BY` it never wrote.
        """
        ...

    def tables(self) -> frozenset[str]:
        """Every table and view in the database, for `table_exists`.

        A set, because the one question anybody asks of it is membership, and an
        order would be an invitation to assert on something SQLite does not
        promise.
        """
        ...

    def plan(self) -> tuple[str, ...]:
        """`EXPLAIN QUERY PLAN` over the answer's final statement, one line each.

        What makes `query_plan_matches` possible, and with it the advisory family
        that is this kind's reason for existing beyond "the rows are right".
        `SCAN orders` in a plan where `SEARCH orders USING INDEX` was available is
        the SQL shape of §4.4's *you achieved the goal, and here is what it cost* —
        exactly the judgement a force-push advisory makes about git.

        Empty rather than `None` when there is no plan to be had, because the
        assertion over it is a pattern match and "no lines matched" is already the
        right answer for "there were no lines".
        """
        ...

    def statements(self) -> tuple[str, ...]:
        """The answer as it was submitted, split into statements.

        The one method here that reads the solver's text rather than the
        database's state, and it exists for the same reason `command_used` reads
        the attempt's command log rather than the repository: some lessons are
        about *how*, and no end state can hold them. A drill that wants "do it
        with a window function, not a correlated subquery" has nowhere else to
        look.

        Advisory by convention, like `command_used`. A required check over the
        text of an answer would be the string matching ADR 0003 rejected.
        """
        ...


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

    def completed(self) -> Sequence[Attempt]:
        """Every attempt that was submitted and graded, oldest first.

        Phase 9's addition, and the counterpart to `active()`: that one is about
        what is still open, this one about what is finished. The progress summary
        needs both halves of each attempt -- when it ended and whether it passed
        -- and neither is derivable from the review cards, which keep no history
        (`sqlite/reviews.py`) and so cannot say which day anything happened on.

        Abandoned attempts are excluded. They have an end timestamp and no
        verdict, so counting one would either shorten a pass rate for work that
        was never graded or extend a streak for a day somebody gave up -- and
        both readings are worse than leaving them out.

        It loads whole aggregates, event logs included, which is the shape
        `sqlite/attempts.py` already names as the one that stops being free "the
        first time a progress page asks for a hundred attempts". That page is
        now here, and the answer for the MVP is that a single-user local history
        is hundreds of rows rather than millions. The replacement when it is not
        is a projection, not a narrower query.
        """
        ...


class ReviewRepository(Protocol):
    """Persistence for scheduling state."""

    def get_card(self, exercise_id: ExerciseId) -> ReviewCard | None: ...

    def save_card(self, card: ReviewCard) -> None: ...

    def due_on(self, day: date) -> Sequence[ReviewCard]: ...

    def cards(self) -> Sequence[ReviewCard]:
        """Every card there is, in exercise-id order.

        Added in Phase 9, and it is not a looser `due_on`. The two answer
        different questions and the review queue needs both: `due_on` is the
        indexed range scan that says *what is due*, longest-overdue first, and
        that ordering is the queue's order; this says *what has ever been
        scheduled*, which is the only way to find the exercises that have not
        been — and an exercise with no card is the most common due item there is,
        so a method returning the due subset can never report one.

        Also what the progress page's mastery and lapse counts read. The whole
        table is a row per exercise in a library of tens, so returning it whole
        costs less than the join a narrower query would need.
        """
        ...


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

    def resolve(self, path: str) -> Path:
        """Where a repository-relative path actually is on disk.

        On the port as of Phase 10, and the one method here that hands out a
        filesystem path rather than its contents. That is the feature and not a
        leak: own-editor mode's whole premise is that the solver's file can be
        opened by a program this app did not write, and an absolute path is the
        only thing an editor, a file watcher or a terminal can be told.

        Confinement is part of the contract. A path that is absolute, or that
        escapes the repository with `..`, is refused rather than clamped — not
        as a security boundary (the solver owns the machine, §8.1) but as a
        blast-radius one: clamping would put a file somewhere the solver then
        has to hunt for.
        """
        ...

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

    def workspaces(self) -> Sequence[WorkspaceSummary]:
        """Every workspace under the root, in a stable order.

        Reports rather than judges: which of these is an orphan is a question about
        the attempt table, and the provisioner has never heard of it. On the port
        from Phase 6 because `CollectWorkspaces` is the thing that answers it, and a
        use case may only see ports.
        """
        ...

    def discard(self, short_id: str) -> None:
        """Delete one workspace by its directory name, whatever is in it.

        Keyed by `short_id` rather than by `AttemptId` for the reason
        `WorkspaceSummary` documents: the leftover most worth collecting is one
        whose metadata was never written, and it has no attempt id to be named by.

        Distinct from `Workspace.dispose` in who calls it and why. `dispose` is an
        attempt tidying up after itself at the end of its own life; this is a
        *third party* removing a directory no attempt owns any more, and it does not
        need — and must not need — the exercise required to attach to one.
        """
        ...


class EditorLauncher(Protocol):
    """Opens one file in whatever editor this machine is set up to use.

    The outward edge of own-editor mode (PLAN.md §11, Phase 10): the solver works
    in their own editor on a real file in the workspace, and this is the thing
    that puts the file in front of them.

    **It returns the problem rather than raising one**, which is the same call
    `RepoQuery` makes and for the same reason: a missing editor is a normal
    outcome a page has to render, not a fault. The feature is *the file is on
    disk at this path* — writing it and saying where it is always works, and the
    launch is the convenience on top. So a failed launch leaves the solver with a
    path they can open themselves, and a traceback would leave them with
    nothing.

    `None` means it was launched. A string is a sentence saying why it was not,
    written to be read — the same shape `interface/web/vendor.verify` uses for
    the problems it reports.
    """

    def reveal(self, path: Path) -> str | None: ...


class FileWatcher(Protocol):
    """Notices when one file is saved, and says so until nobody is listening.

    The other half of own-editor mode: `EditorLauncher` puts the file in front of
    the solver and this is what notices them pressing Ctrl+S. A port rather than
    a direct `watchfiles` call, for two reasons that are both really the same
    one. It keeps a file-watching library out of the layers that must not do
    I/O — `tests/unit/test_architecture.py` names `watchfiles` among the
    modules the domain and the application may not import, so this protocol is
    the only way through. And it is what makes the stream testable: a fake that
    yields a scripted sequence turns *grade on every save* into a unit test,
    where the alternative is racing a real filesystem event and hoping.

    **It yields `False` as well as `True`, and the `False` is load-bearing.**
    `True` means the file changed. `False` is a periodic tick with nothing to
    report, and the caller needs it: an SSE stream that only ever wrote on a
    change has no way to discover that the browser holding it open has gone, and
    would keep a watcher alive per tab that was ever closed. A tick is when the
    web layer gets to check, and it is the reason this is not simply an iterator
    of saves.

    Two implementations, which is what PLAN.md §13 asks: `WatchfilesFileWatcher`
    and the scripted fake in `tests/fakes/watcher.py`.
    """

    def changes(self, path: Path) -> AsyncIterator[bool]: ...


class RepoQuery(Protocol):
    """Read-only git interrogation. The port that makes the check engine pure.

    Every assertion depends on this rather than on a git process, which is what
    lets all 20 of them be unit-tested in milliseconds against an in-memory fake
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


class RepoQueryFactory(Protocol):
    """How a caller gets a `RepoQuery` for a workspace it is holding.

    A port rather than a constructor reference, because two callers need one and
    neither may import an adapter: `ScenarioGrader` builds one per grading pass,
    and as of Phase 8 `InspectRepository` builds one per request that renders the
    repo state panel. It began life as a protocol inside `adapters/git/grader.py`
    and moved here when the second caller appeared — a protocol in an adapter is
    only reachable by that adapter's own collaborators, which was true right up
    until it was not.

    **A call and not a singleton**, which is the whole reason this is shaped as a
    factory. `GitRepoQuery` caches every answer for the life of the instance, so
    six checks asking `status()` between them cost one `git` process; the cache is
    only safe because the instance does not outlive the pass. One kept across a
    solver's commands would answer the panel with the repository as it was before
    the command that prompted the redraw.

    Two implementations from the start, which is what PLAN.md §13 asks of a port:
    `GitRepoQuery` itself — the class is the callable — and a test factory that
    hands back `FakeRepoQuery`, which is what lets the grader's assembly and the
    inspection use case be unit-tested with no git installed.
    """

    def __call__(self, workspace: Workspace) -> RepoQuery: ...


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
    """Moves a review card after an attempt. SM-2 and FSRS, chosen at the root.

    **Two real implementations as of Phase 13**, which is what §13 asks of a port
    and what this one had been carrying an IOU for since Phase 9: `Sm2Scheduler`,
    `FsrsScheduler`, and `FixedScheduler` in the test fakes. The result of
    writing the second one is in ADR 0018 — the protocol itself did not change,
    and `ReviewCard` gained two nullable columns, which is the cost ADR 0008
    predicted to the word.

    `ReviewCard` is the vocabulary both speak, and it is wider than either needs:
    `ease` is SM-2's, `stability` and `difficulty` are FSRS's, and `interval_days`
    is the one number that means the same thing to both. That is what makes a
    switch mid-history survivable rather than a reset.

    **`now` rather than the `today: date` PLAN.md §4.6 sketched**, because the card
    the scheduler returns carries `last_reviewed_at`, and a date cannot produce a
    timestamp. The alternative is a use case patching the returned card, which
    splits one card's construction across two places and lets `due_on` be computed
    from one clock reading while `last_reviewed_at` comes from another — when
    §9.7's fourth property is exactly that the two agree, stated as a property of
    the scheduler. `today` is `now.date()` and the implementation derives it.
    """

    def next_card(
        self, card: ReviewCard, grade: Grade, now: datetime
    ) -> ReviewCard: ...


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
