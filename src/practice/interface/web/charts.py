"""The progress charts as inline SVG, generated in Python.

PLAN.md §8.4 settled the technique before any of it was written: *"charts are
hand-rolled inline SVG generated in Python — zero dependencies, fully offline,
fully server-rendered."* `commit_graph.py` was the first and says most of why;
these two follow the same four rules, and the reasons are worth restating because
they are the ones a charting library would quietly break.

**Colours are CSS custom properties, not literals.** `fill="var(--pass)"` works
in inline SVG and is what keeps a drawing correct under a second colour scheme
without a second palette in Python. A chart that hardcoded `#83c98a` would be the
one element on the page that did not follow the theme.

**Every string is escaped on the way in.** Tag names come from exercise files and
dates are formatted here, so neither is dangerous today — but the rule is the
rule precisely so that nobody has to re-derive which values are safe when a
label starts coming from somewhere else. The result is `Markup`, so no template
needs `| safe`: the escaping decision stays where the escaping happens.

**The geometry is a viewBox and no height.** Served at `width="100%"` over a
fixed `viewBox`, the browser derives the height from the aspect ratio, so a
narrower column scales the drawing down instead of clipping it.

**Every chart says its numbers somewhere a chart cannot be read.** Each bar
carries a `<title>`, the figure carries an `aria-label`, and the page prints the
same counts beside it in text. A chart is the fastest way to see a shape and the
worst way to learn a number, and this one has to work on a printout.

The two differ in one respect worth naming. The activity chart draws *every* day
in the window including the idle ones, because the gaps are the information: a
month with seven scattered attempts and a week with seven consecutive ones are
opposite facts about a habit and would otherwise draw the same picture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from markupsafe import Markup, escape

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.application.progress import DayActivity, Progress, TagMastery

__all__ = ["VIEWPORT_WIDTH", "render_activity", "render_mastery"]

#: The drawing width both charts are laid out in, so two panels side by side
#: scale together. Not pixels — see the module docstring.
VIEWPORT_WIDTH: Final = 400

#: Monospace throughout, so truncation can be computed rather than measured.
#: 6.6 is the advance width of this family at 11px, near enough that a label
#: never overruns the viewBox. The same pair `commit_graph.py` uses.
FONT_SIZE: Final = 11
CHAR_WIDTH: Final = 6.6

_ELLIPSIS: Final = "…"

# --- the activity chart ----------------------------------------------------

#: Bars grow up from the baseline into this, and the axis labels sit under it.
PLOT_HEIGHT: Final = 64
AXIS_HEIGHT: Final = 16

#: The gap between adjacent bars, taken out of each one's share of the width.
#: Fixed rather than proportional so a 7-day window and a 30-day window have the
#: same visual density rather than the same number of gaps.
BAR_GAP: Final = 2.0

#: What an idle day is drawn as. Not nothing: a row of ticks is what makes a
#: mostly-empty window read as a window rather than as one bar floating above a
#: line. Drawn in the *axis* colour rather than the bar colour, which is the
#: correction from looking at it -- in `--ink-dim` the ticks read as data, and a
#: 30-day window with one attempt in it looked like a dashed chart rather than
#: like a month off.
IDLE_HEIGHT: Final = 1.0
IDLE_FILL: Final = "var(--line)"

# --- the mastery chart -----------------------------------------------------

MASTERY_ROW_HEIGHT: Final = 20
MASTERY_BAR_HEIGHT: Final = 10

#: Columns, left to right: the tag, the bar, the count. Fixed widths because the
#: longest tag must not shift the bars of every other row out of alignment --
#: comparing lengths is the only thing this chart is for.
LABEL_WIDTH: Final = 108
COUNT_WIDTH: Final = 56
COLUMN_GAP: Final = 8


def render_activity(progress: Progress) -> Markup:
    """One bar per day of the window, passes filled in.

    Two rectangles per day rather than a stacked pair of series: the outer bar is
    every attempt and the inner one is the passes, drawn over it from the same
    baseline. A stack would put failures *above* passes and make the failing days
    the tall ones, which is the opposite of the reading — height is effort here,
    and colour is how it went.
    """
    days = progress.days
    if not days:
        return Markup('<p class="empty">No window to draw.</p>')

    height = PLOT_HEIGHT + AXIS_HEIGHT
    pitch = VIEWPORT_WIDTH / len(days)
    width = max(1.0, pitch - BAR_GAP)
    # `busiest_day` rather than a max taken here, so two charts drawn from one
    # summary cannot scale differently (`application/progress.py`).
    scale = progress.busiest_day
    body = "".join(
        _day_bar(day, index * pitch, width, scale) for index, day in enumerate(days)
    )
    body += _axis(days)
    return Markup(  # noqa: S704  (every value is escaped or an integer; see module)
        f'<svg class="chart activity" viewBox="0 0 {VIEWPORT_WIDTH} {height}" '
        f'width="100%" preserveAspectRatio="xMinYMin meet" role="img" '
        f'aria-label="{escape(_activity_label(progress))}">{body}</svg>'
    )


def _day_bar(day: DayActivity, x: float, width: float, scale: int) -> str:
    """One day. Always drawn, even when nothing happened — see the module."""
    attempts = _bar_height(day.attempts, scale)
    passed = _bar_height(day.passed, scale)
    fill = IDLE_FILL if day.is_idle else "var(--ink-dim)"
    marks = [_rect(x, attempts, width, fill)]
    if day.passed:
        marks.append(_rect(x, passed, width, "var(--pass)"))
    title = escape(
        f"{day.day.isoformat()}: {day.attempts} attempt"
        f"{'' if day.attempts == 1 else 's'}, {day.passed} passed"
    )
    return f"<g><title>{title}</title>{''.join(marks)}</g>"


def _rect(x: float, height: float, width: float, fill: str) -> str:
    """One bar, standing on the baseline. Both rectangles in a day share this,
    so the outer bar and the filled part cannot sit on different baselines.
    """
    return (
        f'<rect x="{x:.2f}" y="{PLOT_HEIGHT - height:.2f}" width="{width:.2f}" '
        f'height="{height:.2f}" fill="{fill}" rx="1"/>'
    )


def _bar_height(count: int, scale: int) -> float:
    """A day's bar, floored at a visible tick for an idle one.

    `scale` is zero only when the whole window is idle, and dividing by it would
    be the one arithmetic error a chart can make silently — every bar would be
    the same wrong height rather than raising.
    """
    if not count or not scale:
        return IDLE_HEIGHT
    return max(IDLE_HEIGHT, PLOT_HEIGHT * count / scale)


def _axis(days: Sequence[DayActivity]) -> str:
    """The first and last day, written under the ends they belong to.

    Two labels rather than a tick per week. A monospaced `MM-DD` is 33 pixels
    wide and a 30-day window is 400, so weekly ticks would collide at exactly the
    window the chart is sized for — and the question this axis answers is only
    "how far back does this go".
    """
    baseline = PLOT_HEIGHT + 0.5
    y = PLOT_HEIGHT + AXIS_HEIGHT - 4
    first = escape(days[0].day.isoformat()[5:])
    last = escape(days[-1].day.isoformat()[5:])
    return (
        f'<line x1="0" y1="{baseline}" x2="{VIEWPORT_WIDTH}" y2="{baseline}" '
        f'stroke="var(--line)" stroke-width="1"/>'
        f'<text x="0" y="{y}" font-size="{FONT_SIZE}" font-family="monospace" '
        f'fill="var(--ink-dim)">{first}</text>'
        f'<text x="{VIEWPORT_WIDTH}" y="{y}" font-size="{FONT_SIZE}" '
        f'font-family="monospace" fill="var(--ink-dim)" '
        f'text-anchor="end">{last}</text>'
    )


def _activity_label(progress: Progress) -> str:
    total = sum(day.attempts for day in progress.days)
    return (
        f"Activity over {len(progress.days)} days: {total} attempt"
        f"{'' if total == 1 else 's'}, busiest day {progress.busiest_day}"
    )


# --- the mastery chart -----------------------------------------------------


def render_mastery(tags: Sequence[TagMastery]) -> Markup:
    """One horizontal bar per tag, length is the pass rate.

    Sorted by the caller, which is `application/progress.py` — worst first. A
    renderer that sorted would be a second opinion about what "worst" means, and
    the dashboard's weakest-three and this chart would eventually disagree about
    which three.
    """
    if not tags:
        return Markup(
            '<p class="empty">Nothing graded yet, so there is no mastery to show.</p>'
        )

    height = MASTERY_ROW_HEIGHT * len(tags)
    body = "".join(_mastery_row(row, index) for index, row in enumerate(tags))
    return Markup(  # noqa: S704  (as above)
        f'<svg class="chart mastery" viewBox="0 0 {VIEWPORT_WIDTH} {height}" '
        f'width="100%" preserveAspectRatio="xMinYMin meet" role="img" '
        f'aria-label="Pass rate for {len(tags)} tag'
        f'{"" if len(tags) == 1 else "s"}">{body}</svg>'
    )


def _mastery_row(row: TagMastery, index: int) -> str:
    """A label, a track with a bar in it, and the count that bar came from."""
    top = MASTERY_ROW_HEIGHT * index
    text_y = top + MASTERY_ROW_HEIGHT / 2 + FONT_SIZE / 3
    bar_y = top + (MASTERY_ROW_HEIGHT - MASTERY_BAR_HEIGHT) / 2
    track_x = LABEL_WIDTH + COLUMN_GAP
    track_width = VIEWPORT_WIDTH - track_x - COUNT_WIDTH - COLUMN_GAP
    filled = track_width * row.pass_rate

    # A failed or lapsed tag is drawn in the warning colour whatever its rate,
    # so the chart and the dashboard's "weakest" list cannot point at different
    # rows -- `is_weak` is the one answer both read.
    colour = "var(--note)" if row.is_weak else "var(--pass)"
    label = escape(_truncate(str(row.tag), LABEL_WIDTH))
    count = escape(f"{row.passed}/{row.attempted}")
    title = escape(
        f"{row.tag}: {row.passed} of {row.attempted} passed, {row.lapses} lapse"
        f"{'' if row.lapses == 1 else 's'}"
    )
    return (
        f"<g><title>{title}</title>"
        f'<text x="0" y="{text_y:.2f}" font-size="{FONT_SIZE}" '
        f'font-family="monospace" fill="var(--ink)">{label}</text>'
        f'<rect x="{track_x}" y="{bar_y:.2f}" width="{track_width}" '
        f'height="{MASTERY_BAR_HEIGHT}" fill="var(--bg-sunken)" rx="2"/>'
        f'<rect x="{track_x}" y="{bar_y:.2f}" width="{filled:.2f}" '
        f'height="{MASTERY_BAR_HEIGHT}" fill="{colour}" rx="2"/>'
        f'<text x="{VIEWPORT_WIDTH}" y="{text_y:.2f}" font-size="{FONT_SIZE}" '
        f'font-family="monospace" fill="var(--ink-dim)" '
        f'text-anchor="end">{count}</text>'
        f"</g>"
    )


def _truncate(text: str, width: float) -> str:
    """Cut to what fits, with an ellipsis standing in for the rest.

    Computed from the advance width rather than measured, which is what the
    monospace font buys: a renderer that guessed would either wrap a long tag
    over the bars or reserve a column for a length nothing uses.
    """
    limit = int(width / CHAR_WIDTH)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + _ELLIPSIS
