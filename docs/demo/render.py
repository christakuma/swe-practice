"""Turn a captured `practice` session into the animated SVG in the README.

    python docs/demo/render.py

Reads `session.txt` beside this file and writes `docs/demo.svg`.

**Why this exists rather than a GIF.** PLAN.md §11 asked Phase 12 for a demo
GIF and this is what shipped instead, for three reasons that all point the same
way (ADR 0016). A GIF needs a recording tool and an encoder, which means a
dependency this project does not have and will not add — `uv.lock` is resolved
once and deliberately not re-resolved. A GIF is also a picture of text: it
cannot be searched, selected, diffed or read by a screen reader, and a reviewer
who wants to check that the verdict in the README is the verdict the tool
prints has no way to. And `session.txt` is the *real* captured output of a real
command, so the demo is regenerated rather than redrawn — if the verdict's
wording changes, re-running the command and this script is the whole update.

**It degrades to the full transcript rather than to nothing.** Every line is
authored with `opacity="1"` and hidden by the stylesheet, so a renderer that
strips CSS — a Markdown preview, an editor, a sanitiser — shows the complete
session as a static terminal instead of an empty box. That is the opposite of
the usual failure mode for an animated SVG and it is the reason the opacity is
in two places.

Hand-rolled, like the progress charts in `interface/web/charts.py`, and for the
same reason: one small generator with no dependency beats a toolchain for a
picture this simple.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

HERE: Final = Path(__file__).resolve().parent
SESSION: Final = HERE / "session.txt"
OUTPUT: Final = HERE.parent / "demo.svg"

#: Advance width of one character at `FONT_SIZE` in a generic monospace face.
#: Measured rather than assumed: 0.6em is the de-facto advance for Consolas,
#: Menlo and DejaVu Sans Mono alike, which is why the layout can be computed
#: here instead of by the renderer.
CH: Final = 7.8
FONT_SIZE: Final = 13
#: System faces only, as everywhere else in this project: a webfont would put a
#: network request inside an image that documents an offline tool.
FONT_STACK: Final = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
#: What a screen reader is told, since this is a picture of text.
ALT_TEXT: Final = (
    "A terminal replaying practice solve git/revert-a-pushed-commit, which "
    "produces the right files and fails the history-preserved check."
)
LINE_HEIGHT: Final = 19
PAD_X: Final = 22
#: Room for the window chrome above the first line of text.
PAD_TOP: Final = 62
PAD_BOTTOM: Final = 18

#: Seconds for one loop, and the fraction of it spent revealing rather than
#: holding. A third of the loop on the finished screen, because the finished
#: screen is the thing being demonstrated — a cast that wipes the moment it
#: lands is a cast nobody can read.
DURATION: Final = 19.0
REVEAL_FRACTION: Final = 0.66

#: One terminal palette, dark only. The README shows this on both GitHub themes
#: and a themed SVG would need a media query the sanitiser may well drop, so a
#: terminal that looks like a terminal in both is the safer answer.
BACKGROUND: Final = "#13171f"
CHROME: Final = "#1b2029"
FOREGROUND: Final = "#d7dce5"
DIM: Final = "#8b95a7"
GREEN: Final = "#7ec07a"
RED: Final = "#e8716d"
YELLOW: Final = "#d8a657"

#: The three verdict markers the CLI prints, and the indent its continuation
#: lines use. Kept as literals because this script reads the output rather than
#: importing the formatter: a demo generated from the code that produced it
#: could not catch the code changing.
_MARKERS: Final = {"  ok   ": GREEN, "  FAIL ": RED, "  note ": YELLOW}
_CONTINUATION: Final = "         "

#: Prefixes that colour a whole line, tried in order. A table rather than a
#: chain of branches, so adding one is a row instead of another return. The
#: continuation indent is dimmed because that is where the *explanation* of a
#: check lives, and an explanation competing with the verdict for attention is
#: the thing a demo most needs to avoid.
_WHOLE_LINE: Final = (
    (_CONTINUATION, DIM),
    ("graded ", DIM),
    ("  - ", DIM),
    ("FAIL", RED),
    ("PASS", GREEN),
)

#: `git/revert-a-pushed-commit  Undo a commit that is already on origin` -- the
#: heading `solve` prints before anything happens. Matched by shape rather than
#: by line number so that a capture which begins elsewhere still colours it.
_HEADING: Final = re.compile(r"^\S+/\S+ {2}\S")


@dataclass(frozen=True, slots=True)
class Span:
    """A run of characters on one line, and the colour to draw it in."""

    text: str
    fill: str
    bold: bool = False


def spans_for(line: str) -> tuple[Span, ...]:
    """Colour one line of captured output the way the terminal coloured it.

    By prefix, which is exactly how the CLI decides what to print: `_OK`,
    `_BAD` and `_NOTE` are fixed-width markers and everything after one of them
    is the message. Read off the output rather than imported from the
    formatter, deliberately — a demo generated from the code that produced it
    could not catch that code changing.
    """
    if line.startswith("$ "):
        return (Span("$ ", GREEN), Span(line[2:], FOREGROUND, bold=True))
    for marker, fill in _MARKERS.items():
        if line.startswith(marker):
            rest = line[len(marker) :]
            return (Span(marker, fill, bold=True), Span(rest, FOREGROUND))
    for prefix, fill in _WHOLE_LINE:
        if line.startswith(prefix):
            return (Span(line, fill, bold=fill in {RED, GREEN}),)
    return (Span(line, FOREGROUND, bold=bool(_HEADING.match(line))),)


def render(session: str) -> str:
    """The whole SVG, as one string."""
    lines = session.splitlines()
    width = round(PAD_X * 2 + max(len(line) for line in lines) * CH)
    height = round(PAD_TOP + len(lines) * LINE_HEIGHT + PAD_BOTTOM)
    header = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"\n'
        f'     width="{width}" height="{height}" font-size="{FONT_SIZE}"\n'
        f'     font-family="{FONT_STACK}"\n'
        f'     xml:space="preserve" role="img" aria-label="{ALT_TEXT}">'
    )
    return "\n".join(
        [
            header,
            _style(len(lines)),
            _chrome(width, height),
            *(_line(index, text) for index, text in enumerate(lines)),
            "</svg>",
            "",
        ]
    )


def _style(count: int) -> str:
    """One keyframes block per line, so the loop resets cleanly.

    The obvious encoding — one shared animation plus a per-line
    `animation-delay` — does not work with `infinite`: each line then repeats on
    its *own* cycle starting from its delay, so every line flickers off at a
    different moment instead of the screen clearing at once. Giving each line
    its own keyframes, with the reveal point baked in as a percentage of one
    shared duration, makes every animation start and end together.
    """
    rules = [
        "text { white-space: pre }",
        f".l {{ animation: {DURATION}s steps(1, end) infinite both }}",
    ]
    for index in range(count):
        at = round((index + 1) / count * REVEAL_FRACTION * 100, 3)
        rules.append(f".l{index} {{ animation-name: r{index} }}")
        rules.append(
            f"@keyframes r{index} {{ 0%, {at}% {{ opacity: 0 }} "
            f"{at}%, 100% {{ opacity: 1 }} }}"
        )
    body = "\n    ".join(rules)
    return f"  <style>\n    {body}\n  </style>"


def _chrome(width: int, height: int) -> str:
    """A window, so it reads as a terminal rather than as a code block."""
    dots = "".join(
        f'<circle cx="{x}" cy="21" r="5.5" fill="{fill}"/>'
        for x, fill in ((24, "#e8716d"), (44, "#d8a657"), (64, "#7ec07a"))
    )
    return (
        f'  <rect width="{width}" height="{height}" rx="8" fill="{BACKGROUND}"/>\n'
        f'  <path d="M8 0h{width - 16}a8 8 0 0 1 8 8v34H0V8a8 8 0 0 1 8-8z" '
        f'fill="{CHROME}"/>\n'
        f"  {dots}\n"
        f'  <text x="{width / 2}" y="26" fill="{DIM}" font-size="11" '
        f'text-anchor="middle">practice</text>'
    )


def _line(index: int, text: str) -> str:
    """One line of the transcript, positioned and coloured.

    Indentation is left in the text rather than turned into an `x` offset,
    because the markers the colouring keys on (`  ok   `, `  FAIL `) *are* that
    indentation — stripping it would mean classifying one string and drawing
    another. It survives because whitespace is preserved twice over:
    `xml:space="preserve"` on the root, which is an attribute and cannot be
    dropped by a stylesheet sanitiser, and `white-space: pre` for renderers
    that honour the CSS property instead.
    """
    y = round(PAD_TOP + index * LINE_HEIGHT, 1)
    body = "".join(_span(span) for span in spans_for(text))
    return f'  <text class="l l{index}" x="{PAD_X}" y="{y}" opacity="1">{body}</text>'


def _span(span: Span) -> str:
    weight = ' font-weight="600"' if span.bold else ""
    return f'<tspan fill="{span.fill}"{weight}>{_escaped(span.text)}</tspan>'


def _escaped(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main() -> None:
    session = SESSION.read_text(encoding="utf-8")
    # `newline="\n"` because .gitattributes declares LF everywhere and Python's
    # text mode on Windows would write CRLF into a tracked file.
    OUTPUT.write_text(render(session), encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
