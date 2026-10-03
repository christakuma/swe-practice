"""Laying a commit DAG out in lanes. Pure, and the one real algorithm in the app.

**Why this is in `application/` and not in `adapters/git/`.** PLAN.md §10 sketched
an `adapters/git/graph.py` and Phase 5 deliberately did not write it: the only
ancestry question the check engine has is `is_ancestor`, and `git merge-base
--is-ancestor` answers that better than any walk of ours. This is a different
module for a different job. Nothing here asks git anything — it takes the
`CommitInfo` sequence `RepoQuery.log` already returns and decides where to *draw*
it. That makes it a view model, which is the application layer's business, and it
puts it inside the coverage gate, which is where a tangle of index arithmetic
belongs.

**It is not in `domain/` either**, and the line is worth stating: a lane number is
not a rule about exercises or grading. `domain/` holds what the product can be
right or wrong *about*; this holds what a panel looks like.

**The algorithm, and the one property it must have.** Walk the commits in the order
the log gives them — newest first, which is the order a reader scans. Keep an
ordered list of *open lanes*, each holding the sha that lane is currently waiting
for. A commit takes the leftmost lane already waiting for it, or the first free
lane if none is. Its **first parent inherits that lane**, so a linear history is one
straight column and a branch costs a lane only where it genuinely diverges; every
other parent reserves a lane of its own, which is what makes a merge visible as a
line coming in from the side. `git log --graph` makes the same choice, and so does
every tool that has to show a repository someone actually works in.

**Edges are resolved in a second pass, from rows rather than from reservations.**
The first draft built each edge as it reserved the lane, and that is wrong in a way
that only shows up on a merge: two children can both reserve a lane for the same
parent, the parent is eventually drawn in exactly one of them, and an edge built
from the reservation points at a column the commit is not in. So the walk records
*which commit* each link goes to and the lanes are read off the finished rows,
where every endpoint is a position something is actually drawn at.

**A parent outside the window is not an edge.** The panel shows a slice of history,
so a parent off the bottom is the normal case rather than an error — the link is
dropped and the lane closed, instead of being left waiting for a sha that will
never arrive.

`merge_logs` is the other half, and it exists because `RepoQuery.log` answers for
*one* revision. Drawing only what is reachable from HEAD would hide the single most
instructive state these exercises produce: after `git reset --hard HEAD~1` the
commit still on `origin/main` is no longer reachable from HEAD, and a graph that
quietly stopped showing it would conceal exactly the thing the exercise is about.
So the panel asks for a log per distinct ref tip and merges them here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from practice.domain.ids import Sha
    from practice.domain.ports import CommitInfo

__all__ = ["CommitGraph", "GraphEdge", "GraphRow", "lay_out", "merge_logs"]


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """A line from one row's lane down to another row's lane.

    Row indices rather than shas, because what consumes this is a renderer placing
    marks on a grid and resolving a sha to a row is the lookup this module already
    did. `from_row` is always above `to_row`: the log is newest-first, so a parent
    is always further down it.
    """

    from_row: int
    from_lane: int
    to_row: int
    to_lane: int

    @property
    def is_straight(self) -> bool:
        """Whether the line stays in one lane, which is most of them."""
        return self.from_lane == self.to_lane


@dataclass(frozen=True, slots=True)
class GraphRow:
    """One commit, where it sits, and what points at it."""

    commit: CommitInfo
    lane: int
    refs: tuple[str, ...] = ()

    @property
    def is_merge(self) -> bool:
        return self.commit.is_merge


@dataclass(frozen=True, slots=True)
class CommitGraph:
    """A laid-out slice of history: rows top to bottom, edges between them."""

    rows: tuple[GraphRow, ...] = ()
    edges: tuple[GraphEdge, ...] = ()

    @property
    def lanes(self) -> int:
        """How many lanes wide the drawing is. Zero for an empty graph."""
        return max((row.lane for row in self.rows), default=-1) + 1

    @property
    def is_empty(self) -> bool:
        return not self.rows


def lay_out(
    commits: Sequence[CommitInfo],
    *,
    refs: Mapping[str, Sha] | None = None,
    head_ref: str | None = None,
    limit: int | None = None,
) -> CommitGraph:
    """Assign a lane to every commit and an edge to every parent link in the window.

    `limit` truncates *before* laying out rather than after, which is the only order
    that produces a drawing with no dangling edges: an edge to a row that was cut
    away is an edge a renderer has to invent an end for.

    `refs` label the rows they point at, so a commit carries the branches and tags
    on it. Several on one commit is the normal case here — `main` and `origin/main`
    on one tip is the published state the flagship scenario starts in — so a row
    holds a tuple and not a name. `head_ref` sorts to the front of its row's labels,
    because where you are is the thing being looked for.
    """
    window = tuple(commits[:limit] if limit is not None else commits)
    row_of = {commit.sha: index for index, commit in enumerate(window)}
    labels = _labels_by_sha(refs or {}, head_ref=head_ref)

    #: One slot per lane, holding the sha that lane is waiting to draw, or `None`
    #: when the lane is free for reuse.
    lanes: list[Sha | None] = []
    rows: list[GraphRow] = []
    #: `(child row, parent sha)`, resolved to lanes once every row has one.
    links: list[tuple[int, Sha]] = []

    for index, commit in enumerate(window):
        lane = _claim(lanes, commit.sha)
        rows.append(GraphRow(commit=commit, lane=lane, refs=labels.get(commit.sha, ())))

        for position, parent in enumerate(commit.parents):
            if position == 0:
                # The first parent inherits this lane: see the module docstring.
                lanes[lane] = parent
            else:
                _reserve(lanes, parent)
            if parent in row_of:
                links.append((index, parent))
            elif position == 0:
                # Off the bottom of the window, so nothing will ever claim it.
                lanes[lane] = None

        if not commit.parents:
            lanes[lane] = None

    lane_of = [row.lane for row in rows]
    edges = tuple(
        GraphEdge(
            from_row=child,
            from_lane=lane_of[child],
            to_row=row_of[parent],
            to_lane=lane_of[row_of[parent]],
        )
        for child, parent in links
    )
    return CommitGraph(rows=tuple(rows), edges=edges)


def _claim(lanes: list[Sha | None], sha: Sha) -> int:
    """The lane this commit is drawn in, and the place several lines converge.

    *Leftmost* waiting lane, not any waiting lane: keeping the mainline where a
    reader left it beats letting it drift right as branches merge. Every **other**
    lane waiting for the same sha is closed here, which is the step the first draft
    was missing — two children can each reserve a lane for one parent, the parent is
    drawn in exactly one of them, and the rest would otherwise sit reserved forever,
    pushing every later branch a column further right.
    """
    found: int | None = None
    for index, waiting in enumerate(lanes):
        if waiting != sha:
            continue
        if found is None:
            found = index
        else:
            lanes[index] = None
    if found is None:
        found = _open(lanes, sha)
    return found


def _reserve(lanes: list[Sha | None], sha: Sha) -> int:
    """Make sure some lane is waiting for `sha`, without disturbing one that is."""
    for index, waiting in enumerate(lanes):
        if waiting == sha:
            return index
    return _open(lanes, sha)


def _open(lanes: list[Sha | None], sha: Sha) -> int:
    """Take the first closed lane for `sha`, or add one on the right.

    Reusing a closed lane rather than always appending is what stops a history with
    several short-lived branches from drawing a dozen columns wide, almost all of
    them empty.
    """
    for index, waiting in enumerate(lanes):
        if waiting is None:
            lanes[index] = sha
            return index
    lanes.append(sha)
    return len(lanes) - 1


def _labels_by_sha(
    refs: Mapping[str, Sha], *, head_ref: str | None
) -> dict[Sha, tuple[str, ...]]:
    """Full ref names grouped by what they point at, HEAD's own first.

    Full names, as everywhere else refs are carried: shortening is display, and
    `dto.short_ref` owns it. Sorted otherwise, so two renders of one repository
    label a commit the same way round.
    """
    grouped: dict[Sha, list[str]] = {}
    for name, sha in refs.items():
        grouped.setdefault(sha, []).append(name)
    return {sha: tuple(_head_first(names, head_ref)) for sha, names in grouped.items()}


def _head_first(names: Iterable[str], head_ref: str | None) -> list[str]:
    return sorted(names, key=lambda name: (name != head_ref, name))


def merge_logs(logs: Iterable[Sequence[CommitInfo]]) -> tuple[CommitInfo, ...]:
    """Several newest-first logs into one order that respects all of them.

    **Every commit comes before its own parents**, which is the one property
    `lay_out` depends on: it walks downwards reserving a lane for each parent, and
    a parent emitted *above* its child would be drawn before anything had reserved
    a lane for it.

    Kahn's algorithm over the parent links, with the tiebreak being where a commit
    first appeared in the concatenated input. That makes the result deterministic
    and keeps the first log's shape -- usually HEAD's -- running down the left of
    the drawing, with the others folded in where they belong rather than appended
    in a block.

    **Commit dates are not used, because `CommitInfo` does not carry one**, and the
    alternative is adding a field to a port value object for the benefit of one
    renderer. Git orders its own log by date; this orders by reachability and input
    position, which differs from git only between commits neither of which can
    reach the other -- where any order is defensible and only stability matters.
    """
    commits: dict[Sha, CommitInfo] = {}
    rank: dict[Sha, int] = {}
    for log in logs:
        for commit in log:
            if commit.sha not in commits:
                commits[commit.sha] = commit
                rank[commit.sha] = len(rank)

    waiting_on = {
        sha: sum(1 for child in commits.values() if sha in child.parents)
        for sha in commits
    }
    ready = sorted(
        (sha for sha, count in waiting_on.items() if count == 0), key=rank.__getitem__
    )

    ordered: list[CommitInfo] = []
    while ready:
        sha = ready.pop(0)
        ordered.append(commits[sha])
        for parent in commits[sha].parents:
            if parent not in waiting_on:
                continue
            waiting_on[parent] -= 1
            if waiting_on[parent] == 0:
                ready.append(parent)
        ready.sort(key=rank.__getitem__)

    # A cycle is not a thing git can produce, and silently dropping commits would
    # be the worst way to find out otherwise -- so anything left over is appended
    # in input order rather than lost.
    ordered.extend(
        commits[sha]
        for sha in sorted(rank, key=rank.__getitem__)
        if waiting_on.get(sha, 0) > 0
    )
    return tuple(ordered)
