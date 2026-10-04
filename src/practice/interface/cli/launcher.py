"""What `practice up` checks and creates before it serves anything.

**The failure this module exists for is a cryptic 500 on a stranger's first
submission.** Everything the app needs is discovered lazily and in the right
place for the long run — git is resolved per command, the database migrates on
first write, the content root is read when a page asks for a list. Each of those
is correct and each of them surfaces a missing prerequisite in the middle of an
HTTP request, which is the worst available moment: the browser shows a stack
trace, the terminal shows a traceback from a threadpool, and neither says
*install git*. So the launcher asks all five questions up front, while there is
still a terminal to answer in (PLAN.md §11, Phase 12).

**Five steps, run unconditionally, and all their problems reported together.**
The tempting shape is a chain that stops at the first failure, and it is the
wrong one for a tool somebody has just cloned: a machine with no git very
plausibly also has no writable data directory, and two runs to learn two facts
is one run too many. So every step runs and `FirstRun` collects them, which is
also why each step catches its own exceptions and turns them into a sentence
rather than letting one propagate and take the other three with it.

The cost of that choice is a side effect on a run that then refuses: the
workspace directory and the database file are created even if git is missing.
That is deliberate and it is cheap — both are empty, both are where they would
have been created on the first attempt anyway, and the alternative is a report
that cannot tell you whether the *next* thing is also broken.

**The steps are ordered by how early they stop you, not by cost.** git first:
with no git there is no fixture, no attempt and no grading, so it is the one
whose absence makes the other three pointless. Then the library, because an
empty content root is a server with nothing to offer. Then the two pieces of
local state, which are the ones this module actually creates. The scheduler is
last because it stops you latest of the five — not until the first *review*,
which is after a whole exercise has been solved.

**The fifth step was added in Phase 13, and the blocker is not its main job.**
A bad `PRACTICE_SCHEDULER` would already fail loudly, at `build_services`, before
a request existed — so turning it into a sentence rather than a traceback is a
small win. The larger one is the same one `Step.detail` exists for everywhere
else: the report says *which* git and *which* directory because a solver with
two git installations is not helped by the word "ok", and which algorithm is
moving their cards is exactly that kind of fact. It is a choice with
consequences they cannot otherwise see.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.adapters.content import ContentError, FilesystemContentRepository
from practice.adapters.persistence import Database
from practice.adapters.persistence.sqlite import MigrationError, load_migrations
from practice.adapters.sandbox import ToolNotFoundError, find_git
from practice.composition import build_scheduler
from practice.domain.errors import InvalidValueError
from practice.domain.exercise import ExerciseKind

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["FirstRun", "Step", "prepare"]


@dataclass(frozen=True, slots=True)
class Step:
    """One prerequisite, and what was found when it was asked about.

    `detail` is filled in on success as well as on failure, because the useful
    half of a first-run report is *which* git and *which* directory — a solver
    with two git installations or a stale `PRACTICE_CONTENT_ROOT` is not helped
    by the word "ok".
    """

    label: str
    detail: str
    #: Why this blocks, phrased as the fix. `None` when the step passed.
    problem: str | None = None

    @property
    def ok(self) -> bool:
        return self.problem is None


@dataclass(frozen=True, slots=True)
class FirstRun:
    """Every step, in the order they were asked, plus whether this was one.

    `fresh` is about the *database* and not about the machine: it is the one
    piece of state here that cannot be regenerated (`config.py`), so "this run
    created your attempt history" is worth saying once and never again.
    """

    steps: tuple[Step, ...]
    fresh: bool

    @property
    def ok(self) -> bool:
        return all(step.ok for step in self.steps)

    @property
    def blockers(self) -> tuple[Step, ...]:
        return tuple(step for step in self.steps if not step.ok)


def prepare(
    *, content: Path, workspaces: Path, database: Path, scheduler: str
) -> FirstRun:
    """Check what cannot be fixed later, create what can, and report both.

    Takes its inputs rather than reading `config.py` itself, so that the command
    passes the same resolved values it then hands `build_services` — a report
    about a different content root, or a different scheduler, than the one being
    served would be worse than no report.
    """
    storage = Database(database)
    fresh = not storage.exists
    return FirstRun(
        steps=(
            _git(),
            _library(content),
            _workspaces(workspaces),
            _database(storage, fresh=fresh),
            _scheduler(scheduler),
        ),
        fresh=fresh,
    )


def _git() -> Step:
    """Resolve the git this process would use, without running it.

    Resolution rather than `git --version`, and the distinction is worth being
    explicit about: running it would mean starting a process from outside the
    sandbox, which the architecture test forbids for good reason, and would
    prove a version this tool does not actually have a floor for. What breaks a
    stranger's first attempt is git not being *found* — the `ToolNotFoundError`
    below is the one `practice start` would have raised twenty seconds later.
    """
    try:
        git = find_git()
    except ToolNotFoundError as exc:
        return Step(label="git", detail="not found", problem=str(exc))
    return Step(label="git", detail=str(git))


def _library(root: Path) -> Step:
    """Count the exercises, by kind, through the repository the app will use.

    Through `FilesystemContentRepository` rather than `validate_library`, which
    is the heavier audit `practice validate` runs: this has to be fast enough to
    sit in front of every launch, and the question it answers is "is there a
    library here at all", not "is every file in it well-formed". A malformed
    exercise is a `practice validate` finding; an empty or wrong content root is
    this one, and it is the one that silently produces an app with no content.

    **A `ContentError` is caught here anyway, and it is not a duplicate of
    `validate`.** The repository fails the *whole* listing on one broken
    exercise, deliberately, so that an exercise cannot vanish quietly — which
    means one bad file is not a smaller library, it is a browse page that 500s.
    Catching it turns that into "run `practice validate`", which is the command
    that names the field and the line.
    """
    try:
        exercises = FilesystemContentRepository(root).list_exercises()
    except ContentError as exc:
        return Step(
            label="library",
            detail=str(root),
            problem=(
                f"an exercise under {root} could not be loaded, so the whole "
                f"library fails to list; run `practice validate` for the "
                f"details:\n{exc}"
            ),
        )
    except OSError as exc:
        return Step(
            label="library",
            detail=str(root),
            problem=f"the exercise library at {root} could not be read ({exc})",
        )
    katas = sum(1 for one in exercises if one.kind is ExerciseKind.KATA)
    scenarios = len(exercises) - katas
    if not exercises:
        return Step(
            label="library",
            detail=str(root),
            problem=(
                f"there are no exercises under {root}; point --content-root at a "
                f"library, or run this from a checkout that has content/"
            ),
        )
    # ASCII only, and not a stylistic preference: `chcp 437` is still the
    # default on a fresh Windows console, and an em dash arrives there as a
    # replacement character. This is the first line a stranger reads.
    return Step(
        label="library",
        detail=(
            f"{len(exercises)} exercises ({scenarios} git "
            f"{_plural('scenario', scenarios)}, {katas} "
            f"{_plural('kata', katas)}) in {root}"
        ),
    )


def _workspaces(root: Path) -> Step:
    """Create the directory attempts are provisioned into.

    Created here rather than left to the provisioner so that a read-only or
    full disk is reported now. It is under the user *cache* deliberately
    (`config.py`), which is the other half of why this is safe to create
    eagerly: an empty cache directory is not state anybody can lose.
    """
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return Step(
            label="workspaces",
            detail=str(root),
            problem=f"{root} could not be created ({exc})",
        )
    return Step(label="workspaces", detail=str(root))


def _database(storage: Database, *, fresh: bool) -> Step:
    """Apply every migration now, rather than on the first submission.

    This is the step with the most to gain from being early. `Database.migrate`
    refuses a history it cannot apply — a gap in the numbered files, or a file
    written by a newer `practice` than this one — and that refusal arriving
    mid-submission is a 500 over an attempt the solver has already done the work
    for. Here it is a sentence and an exit code before anything is at stake.

    Idempotent, so this costs one connection on every launch after the first.
    """
    try:
        storage.migrate()
    except MigrationError as exc:
        return Step(
            label="database",
            detail=str(storage.path),
            problem=f"the database at {storage.path} cannot be migrated: {exc}",
        )
    except OSError as exc:
        return Step(
            label="database",
            detail=str(storage.path),
            problem=f"{storage.path} could not be opened ({exc})",
        )
    version = load_migrations()[-1].version
    state = "created" if fresh else "schema"
    return Step(
        label="database",
        detail=f"{storage.path} ({state} v{version})",
    )


def _scheduler(name: str) -> Step:
    """Resolve the configured scheduler, and say which one it is.

    Built rather than looked up, which is the only way to be sure: both
    schedulers validate on construction — `FsrsScheduler` refuses anything but
    seventeen parameters — so a name that maps to a class that cannot be
    instantiated is caught here rather than at the first review.

    The `repr` is the detail, because that is where each scheduler says what is
    actually in force; `FsrsScheduler`'s reports whether its parameters are the
    published defaults, which is the one thing worth knowing about numbers this
    project cannot validate (ADR 0018).
    """
    try:
        chosen = build_scheduler(name)
    except InvalidValueError as exc:
        return Step(label="scheduler", detail=name, problem=str(exc))
    return Step(label="scheduler", detail=f"{name} ({chosen!r})")


def _plural(noun: str, count: int) -> str:
    return noun if count == 1 else f"{noun}s"
