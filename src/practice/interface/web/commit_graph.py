"""The commit graph as inline SVG, generated in Python.

PLAN.md §8.4 settled the technique before this was written: *"charts are hand-rolled
inline SVG generated in Python — zero dependencies, fully offline, fully
server-rendered."* This is the first of them, and Phase 9's progress charts follow
the same rule.

**Why SVG and not a text graph.** §11 sketched "text lanes first, then the SVG
renderer", which is risk sequencing rather than two deliverables: the risky half is
the *lane model*, and that is `application/graph.py`, proved by its own unit tests
with no renderer involved at all. Once the model was green there was nothing a text
rendering would have established that the SVG does not, and shipping both would
have meant two drawings of one model, drifting.

**Text goes in the same SVG as the lanes, not in an HTML column beside it.** The
obvious alternative — SVG for the lanes, a list for the subjects, aligned by row
height — needs two coordinate systems to agree about a 22-pixel pitch, in two files,
forever. One document aligns by construction.

**Colours are CSS custom properties, not literals.** `fill="var(--ink-dim)"` works
in inline SVG and is what keeps the drawing correct under the light scheme without a
second palette here. A renderer that hardcoded `#dfe3ec` would be invisible on the
light theme and nothing would notice until someone looked.

**Every string is escaped on the way in.** Commit subjects and ref names come out of
a repository the solver has been typing into, so `<title>Fix &lt;script&gt;</title>`
is the normal path. The result is `Markup` so the template does not have to decide:
the escaping happened where the markup was built.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from markupsafe import Markup, escape

if TYPE_CHECKING:
    from practice.application.graph import CommitGraph, GraphEdge, GraphRow

__all__ = ["VIEWPORT_WIDTH", "render_graph"]

#: The drawing's own coordinate width. The `svg` is served at `width="100%"` over
#: this `viewBox` and with **no height attribute**, so the browser derives the
#: height from the aspect ratio and a narrower column scales the whole drawing
#: down rather than clipping it or letterboxing it -- which is the behaviour a
#: panel in a responsive grid has to have. `xMinYMin` anchors it top-left, since a
#: graph floated in the middle of its own box reads as a misalignment.
VIEWPORT_WIDTH: Final = 400

#: Vertical pitch, and the y of the first row's centre. One constant each, because
#: the lanes and the text are placed from the same pair.
ROW_HEIGHT: Final = 22
FIRST_ROW_Y: Final = 14

#: Horizontal pitch of the lanes, and where lane 0's centre sits.
LANE_WIDTH: Final = 13
FIRST_LANE_X: Final = 9

#: Commit markers. A merge is drawn hollow so it is identifiable at a glance in a
#: drawing whose other distinguishing feature -- a second line coming in -- is the
#: thing a reader is trying to find.
DOT_RADIUS: Final = 4.0
MERGE_RADIUS: Final = 4.5

#: Monospace throughout, so the truncation below can be computed rather than
#: measured. 6.6 is the advance width of this family at 11px, near enough that a
#: label never overruns the viewBox.
FONT_SIZE: Final = 11
CHAR_WIDTH: Final = 6.6

#: Gap between the rightmost lane and the start of the text.
TEXT_GAP: Final = 8

#: How much of a hash to print. Git's own default floor, and enough to be unique in
#: a repository of a dozen commits.
SHA_LENGTH: Final = 7

#: What stands in for the part of a subject that did not fit. The refs and the
#: hash are laid out first and the subject takes what is left, because a branch
#: name pushed off the right edge is the more costly of the two to lose.
_ELLIPSIS: Final = "…"


def render_graph(graph: CommitGraph) -> Markup:
    """One `<svg>` for a laid-out graph, or an empty-state note for an empty one.

    Not a `<p>` smuggled out of a function that promises SVG: an empty graph is a
    repository with no commits on any ref, which is a real state (a fixture whose
    history a solver has just thrown away), and the panel needs *something* legible
    there. The caller renders whatever comes back.
    """
    if graph.is_empty:
        return Markup('<p class="empty">No commits on any ref — nothing to draw.</p>')

    height = FIRST_ROW_Y + ROW_HEIGHT * (len(graph.rows) - 1) + FIRST_ROW_Y
    body = "".join(
        [
            *(_edge(edge) for edge in graph.edges),
            *(_dot(row, index) for index, row in enumerate(graph.rows)),
            *(_label(row, index, graph.lanes) for index, row in enumerate(graph.rows)),
        ]
    )
    # S704 is right to ask about every `Markup` built from a non-literal, and the
    # answer is in this module's docstring: every value from the repository goes
    # through `escape` at the point it is interpolated, and everything else here is
    # an integer from the layout. The alternative -- returning a plain `str` and
    # putting `| safe` in the template -- moves the same decision somewhere with
    # less of the context needed to make it.
    return Markup(  # noqa: S704
        f'<svg class="commit-graph" viewBox="0 0 {VIEWPORT_WIDTH} {height}" '
        f'width="100%" preserveAspectRatio="xMinYMin meet" role="img" '
        f'aria-label="Commit graph, {len(graph.rows)} commits">{body}</svg>'
    )


def _x(lane: int) -> float:
    return FIRST_LANE_X + LANE_WIDTH * lane


def _y(row: int) -> float:
    return FIRST_ROW_Y + ROW_HEIGHT * row


def _edge(edge: GraphEdge) -> str:
    """A vertical line, or a curve for the few links that change lane.

    The curve's control points sit a little over half a row from each end, which is
    what makes a branch leave its parent at a visible angle instead of as a
    diagonal across two rows -- the shape that makes a three-way merge unreadable.
    """
    x1, y1 = _x(edge.from_lane), _y(edge.from_row)
    x2, y2 = _x(edge.to_lane), _y(edge.to_row)
    if edge.is_straight:
        path = f"M{x1},{y1} L{x2},{y2}"
    else:
        bend = ROW_HEIGHT * 0.6
        path = f"M{x1},{y1} C{x1},{y1 + bend} {x2},{y2 - bend} {x2},{y2}"
    return f'<path class="lane" d="{path}" />'


def _dot(row: GraphRow, index: int) -> str:
    radius = MERGE_RADIUS if row.is_merge else DOT_RADIUS
    kind = "merge" if row.is_merge else "commit"
    return (
        f'<circle class="node {kind}" cx="{_x(row.lane)}" cy="{_y(index)}" '
        f'r="{radius}" />'
    )


def _label(row: GraphRow, index: int, lanes: int) -> str:
    """The hash, the refs on this commit, and the subject, truncated to fit.

    `<title>` carries the untruncated subject, which is the honest way to shorten
    something: the full text is one hover away rather than gone. It is also what a
    screen reader reads for the group.
    """
    x = _x(lanes - 1) + TEXT_GAP
    budget = int((VIEWPORT_WIDTH - x) / CHAR_WIDTH)
    sha = row.commit.sha.value[:SHA_LENGTH]
    refs = " ".join(_short(name) for name in row.refs)

    spent = len(sha) + 1 + (len(refs) + 1 if refs else 0)
    subject = _fit(row.commit.subject, budget - spent)

    pieces = [f'<tspan class="sha">{escape(sha)}</tspan>']
    if refs:
        pieces.append(f'<tspan class="refs"> {escape(refs)}</tspan>')
    pieces.append(f"<tspan> {escape(subject)}</tspan>")
    return (
        f'<text class="row" x="{x}" y="{_y(index) + 4}" font-size="{FONT_SIZE}">'
        f"<title>{escape(row.commit.subject)}</title>"
        f"{''.join(pieces)}</text>"
    )


def _short(ref: str) -> str:
    """`refs/heads/main` -> `main`, without importing the application's filter.

    A second copy of three string prefixes, and a deliberate one: this module is a
    renderer, and reaching across to `dto.short_ref` for it would couple the
    drawing to a DTO it otherwise never touches. The thing that must not be
    duplicated is the *rule*, and the rule -- strip the prefix, never split on the
    last slash -- is stated in both places and tested in both.
    """
    for prefix in ("refs/heads/", "refs/remotes/", "refs/tags/"):
        if ref.startswith(prefix):
            return ref.removeprefix(prefix)
    return ref


def _fit(text: str, budget: int) -> str:
    """`text`, or as much of it as fits with an ellipsis standing for the rest."""
    if budget <= 1:
        return ""
    if len(text) <= budget:
        return text
    return text[: budget - 1].rstrip() + _ELLIPSIS
