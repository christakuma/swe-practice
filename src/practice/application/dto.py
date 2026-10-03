"""What a use case hands back.

Thin on purpose. These carry domain objects rather than flattening them into
display strings, because two very different adapters read them — a Typer command
and a Jinja template — and whichever one formatted first would end up owning the
formatting for the other.

What they *do* add is the join. A caller holding an `Attempt` has an
`ExerciseId` and not an `Exercise`, so rendering anything at all means another
trip to the content repository; returning both together is what stops every
route and every command from making that trip itself and disagreeing about what
to do when it misses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import date

    from practice.application.graph import CommitGraph
    from practice.domain.attempt import Attempt, CommandRun
    from practice.domain.exercise import Exercise, Hint
    from practice.domain.ids import Sha
    from practice.domain.ports import Workspace, WorkspaceSummary, WorktreeStatus
    from practice.domain.review import Grade, ReviewCard
    from practice.domain.scheduling import GradeSuggestion
    from practice.domain.verdict import Outcome, Verdict

__all__ = [
    "Abandoned",
    "Collection",
    "DueExercise",
    "OpenAttempt",
    "RanCommand",
    "RepoView",
    "RevealedHint",
    "ReviewOffer",
    "Reviewed",
    "StartedAttempt",
    "Submission",
    "Workbench",
    "WorkspaceState",
    "short_ref",
]


@dataclass(frozen=True, slots=True)
class StartedAttempt:
    """A provisioned attempt, ready to be worked on.

    The `Workspace` is included because the caller that started the attempt is
    usually the one about to write a file into it, and making it attach again to
    get a handle it was just given would be ceremony. A caller in a *different*
    process — the web app, a second CLI invocation — goes through
    `SandboxProvisioner.attach` instead, which is why nothing downstream of this
    assumes the object is still live.
    """

    attempt: Attempt
    exercise: Exercise
    workspace: Workspace

    @property
    def prompt(self) -> str:
        return self.exercise.prompt


@dataclass(frozen=True, slots=True)
class Submission:
    """A graded, completed attempt."""

    attempt: Attempt
    exercise: Exercise
    verdict: Verdict

    @property
    def outcome(self) -> Outcome:
        """Derived by the verdict, never stored — see `Verdict.outcome`."""
        return self.verdict.outcome

    @property
    def passed(self) -> bool:
        """True for a pass with advisories too: the goal was met either way."""
        return self.verdict.passed


@dataclass(frozen=True, slots=True)
class RanCommand:
    """One command, as the attempt now remembers it.

    The `CommandRun` rather than the bare `CommandResult`, because the caller wants
    the things only the aggregate knows: when it happened, and the normalised line it
    was recorded as. The attempt comes with it so a console can redraw its budget
    without a second lookup -- `remaining_commands` is the number a solver watches.
    """

    attempt: Attempt
    exercise: Exercise
    command: CommandRun

    @property
    def remaining_commands(self) -> int:
        return self.attempt.remaining_commands

    @property
    def succeeded(self) -> bool:
        """A failing command is a normal outcome, often the instructive one."""
        return self.command.result.succeeded


@dataclass(frozen=True, slots=True)
class RevealedHint:
    """One hint, and where it sits in the sequence.

    `index` as well as the hint, because the thing that makes a progressive reveal
    legible is knowing *which* one this is -- "hint 2 of 4" -- and because the
    attempt's log records the position for exactly the same reason: so it still
    says which hint was shown after the exercise is edited.

    The attempt comes with it so a page can redraw the counter without a second
    lookup, which is the same join `RanCommand` makes for the command budget.
    """

    attempt: Attempt
    exercise: Exercise
    hint: Hint
    index: int

    @property
    def number(self) -> int:
        """1-based, because that is how it is spoken about. `index` stays 0-based,
        because that is how the policy's list is addressed and how the log stores
        it -- converting in one direction at the edge beats two conventions in the
        middle.
        """
        return self.index + 1

    @property
    def remaining(self) -> int:
        return self.attempt.remaining_hints


@dataclass(frozen=True, slots=True)
class OpenAttempt:
    """One attempt still in flight, and the two facts a prompt needs about it.

    `exercise` is optional where every other DTO's is not, and that is the honest
    encoding rather than a convenience: an exercise can be renamed or deleted from
    the library under a live attempt, and the resulting attempt is one that can be
    *abandoned* and never graded. A listing that refused to show it would hide the
    only thing that can be done about it.

    `workspace_on_disk` is what separates the two offers. An attempt whose workspace
    has been collected cannot be resumed, so a prompt that did not know this would
    offer a choice that cannot be taken.
    """

    attempt: Attempt
    exercise: Exercise | None
    workspace_on_disk: bool

    @property
    def label(self) -> str:
        """The exercise's title, or its id when the library no longer has it."""
        if self.exercise is None:
            return f"{self.attempt.exercise_id} (no longer in the library)"
        return self.exercise.title

    @property
    def can_resume(self) -> bool:
        return self.workspace_on_disk and self.exercise is not None


@dataclass(frozen=True, slots=True)
class Abandoned:
    """An attempt given up on, and the workspace that went with it.

    Carries the attempt so a caller can report when it started and how far it got
    -- the log survives, which is the difference between abandoning an attempt and
    deleting its row.
    """

    attempt: Attempt
    exercise: Exercise | None


@dataclass(frozen=True, slots=True)
class Workbench:
    """One attempt, rendered -- in whatever state it is in.

    The DTO a *page* needs rather than one a command does, and the difference is
    the whole reason it exists: `StartedAttempt` describes a live session and
    `Submission` describes a graded one, and a URL has to render either. A tab
    left open across a submission asks for the same id and must get a verdict
    rather than an error.

    `workspace` is `None` once the attempt is finished, because submission
    disposes of it -- that is the expected state, not the broken one. For an
    attempt still `ACTIVE`, a missing workspace is `WorkspaceGoneError` and never
    reaches here.

    `editor_source` is `None` for a git scenario, whose surface is a console and
    not an editor, and for a finished kata, which has a verdict to show instead.
    Two different reasons and one value, which is the honest encoding: the
    question the template asks is "is there an editor on this page".
    """

    attempt: Attempt
    exercise: Exercise
    workspace: Workspace | None
    editor_source: str | None = None

    @property
    def is_active(self) -> bool:
        return self.attempt.is_active

    @property
    def verdict(self) -> Verdict | None:
        """The attempt's own, which is `None` until it has one."""
        return self.attempt.verdict

    @property
    def has_editor(self) -> bool:
        return self.editor_source is not None


@dataclass(frozen=True, slots=True)
class RepoView:
    """One repository, as a panel needs to read it.

    **The port's vocabulary, re-grouped — not reformatted.** `WorktreeStatus` and
    `Sha` come through as they are, for the reason this module's docstring gives:
    two adapters read these, and whichever formatted first would own the other's
    formatting. What this adds is the grouping a reader of a repository wants and
    `RepoQuery` has no opinion about — local branches apart from remote-tracking
    ones apart from tags — because `refs()` answers with one flat map of full ref
    names, correctly: `branch_exists {name: main}` and `tag_exists {name: main}`
    have to be able to disagree.

    **`head_ref` is `None` exactly when HEAD is detached**, which is the one fact
    about a repository this panel exists to make unmissable. It is also why the
    field is the ref name rather than a `bool`: a page showing "detached" and
    nothing else has told you the diagnosis and withheld the evidence.

    `stashes` is the list rather than a count. A stash's message is the only clue
    to what is in it, and "1 stash" is the version of this that sends someone to
    the terminal.

    `graph` is already laid out, and that is not a shortcut. It is a view model
    over the same `CommitInfo` values -- `application/graph.py` says why it lives
    one layer in from the renderer -- and building it here means one inspection
    produces one consistent answer: refs, status and drawing all read from a single
    `RepoQuery` instance rather than from three taken a moment apart.
    """

    head_ref: str | None
    head_sha: Sha | None
    status: WorktreeStatus
    branches: Mapping[str, Sha]
    remote_branches: Mapping[str, Sha]
    tags: Mapping[str, Sha]
    stashes: Sequence[str]
    graph: CommitGraph

    @property
    def is_detached(self) -> bool:
        """Derived, never stored, for the same reason `Verdict.outcome` is: there
        is then no code path that can claim a ref and a detached HEAD at once.
        """
        return self.head_ref is None

    @property
    def head_branch(self) -> str | None:
        """`refs/heads/main` as `main`, or `None` when HEAD is detached.

        Short here and full on the port, which is the division that keeps both
        honest: the ref map has to be unambiguous because assertions read it, and
        a panel has to be readable because people do.
        """
        if self.head_ref is None:
            return None
        return short_ref(self.head_ref)

    @property
    def is_unborn(self) -> bool:
        """HEAD names a branch that has no commit yet.

        A real state and a reachable one — `git init` followed by nothing, or a
        fixture whose first commit a solver has just reset away — and one the panel
        has to say out loud, because every other field being empty looks like a
        panel that failed to load rather than a repository with nothing in it.
        """
        return self.head_sha is None


def short_ref(name: str) -> str:
    """`refs/heads/main` -> `main`, `refs/remotes/origin/main` -> `origin/main`.

    **Prefix-stripping, never a split on the last slash.** A branch may legally be
    called `feature/parser`, and taking the last segment would display two
    different branches under one name — a panel actively lying about what is in the
    repository, which is worse than no panel.

    Public, and the only display helper in this module, because the ref *maps* keep
    their full names: assertions read them and `branch_exists {name: main}` has to
    be able to disagree with `tag_exists {name: main}`. So the shortening happens at
    the point of display, where the kind is already known from which map it came
    out of, and the web layer registers this as a Jinja filter rather than keeping
    a second copy of the prefix list.
    """
    for prefix in ("refs/heads/", "refs/remotes/", "refs/tags/"):
        if name.startswith(prefix):
            return name.removeprefix(prefix)
    return name


# --- scheduling ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReviewOffer:
    """A graded attempt, the card behind it, and what the tool would grade it.

    The read half of the review pair. `card` is `None` for an exercise that has
    never been scheduled, which is the normal first time and not a gap: the
    repository refuses to manufacture one, because a card invented on the spot
    would make "has this ever been reviewed?" unanswerable (`memory.py`).

    **`already_reviewed` lives here rather than in the use case that enforces
    it**, so the panel that hides the buttons and the use case that refuses the
    post cannot disagree about which attempts are still open to review.
    """

    attempt: Attempt
    exercise: Exercise
    card: ReviewCard | None
    suggestion: GradeSuggestion

    @property
    def suggested(self) -> Grade:
        return self.suggestion.grade

    @property
    def already_reviewed(self) -> bool:
        """Whether *this* attempt has already moved the card.

        Compared on timestamps rather than counted, because the card keeps no
        history (`sqlite/reviews.py`) and so cannot be asked which attempt last
        moved it. A card reviewed at or after the attempt finished was moved by
        this attempt -- nothing else could have happened in between -- and
        reviewing it again would advance the interval twice for one piece of
        evidence.
        """
        finished_at = self.attempt.finished_at
        if self.card is None or self.card.last_reviewed_at is None:
            return False
        # An unfinished attempt cannot have been reviewed, and the use cases
        # refuse one before they ever build this -- but the DTO is constructible
        # and answering `True` for an attempt with no end would be a refusal
        # nobody could clear.
        return finished_at is not None and self.card.last_reviewed_at >= finished_at


@dataclass(frozen=True, slots=True)
class Reviewed:
    """A card that has just been moved, and what moved it.

    `suggestion` comes along with the grade that was actually used so a surface
    can say whether the solver took the tool's reading or overrode it -- which is
    the only feedback the suggestion rule will ever get.
    """

    attempt: Attempt
    exercise: Exercise
    card: ReviewCard
    grade: Grade
    suggestion: GradeSuggestion

    @property
    def followed_the_suggestion(self) -> bool:
        return self.grade is self.suggestion.grade

    @property
    def interval_days(self) -> int:
        """How long until this comes back. The number a solver actually reads."""
        return self.card.interval_days


@dataclass(frozen=True, slots=True)
class DueExercise:
    """One row of the review queue: an exercise, and why it is being offered.

    `card` is `None` for an exercise that has never been scheduled, and those are
    offered too. A queue that only listed cards would be empty on a fresh install
    with the whole library unpractised -- which is the one state where "what
    should I practice today?" most needs an answer.

    `today` is carried rather than reached for so that `days_overdue` is a
    property of the row and not of the moment it is rendered: a page built at
    23:59 and read at 00:01 says the same thing it said when it was built.
    """

    exercise: Exercise
    card: ReviewCard | None
    today: date

    @property
    def is_new(self) -> bool:
        return self.card is None

    @property
    def days_overdue(self) -> int:
        """Zero for a new exercise and for one due exactly today."""
        if self.card is None:
            return 0
        return max(0, (self.today - self.card.due_on).days)


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    """One workspace on disk, and whether an active attempt still owns it.

    The orphan rule of PLAN.md 8.1, as a value: `in_use` is the join against the
    attempt table, and everything else is what the provisioner found.
    """

    workspace: WorkspaceSummary
    in_use: bool

    @property
    def is_orphan(self) -> bool:
        """A workspace with no corresponding `active` attempt row. Collectable."""
        return not self.in_use


@dataclass(frozen=True, slots=True)
class Collection:
    """What `practice gc` found, and what it did about it.

    The same classification whether or not anything was deleted, so a dry run and a
    real one cannot disagree about what counts as an orphan -- which is the bug that
    makes a destructive command untrustworthy.
    """

    workspaces: tuple[WorkspaceState, ...]
    deleted: tuple[str, ...]

    @property
    def orphans(self) -> tuple[WorkspaceState, ...]:
        return tuple(state for state in self.workspaces if state.is_orphan)

    @property
    def in_use(self) -> tuple[WorkspaceState, ...]:
        return tuple(state for state in self.workspaces if state.in_use)

    @property
    def total_bytes(self) -> int:
        return sum(state.workspace.size_bytes for state in self.workspaces)

    @property
    def reclaimable_bytes(self) -> int:
        """What collecting would free, which is the number worth printing."""
        return sum(state.workspace.size_bytes for state in self.orphans)
