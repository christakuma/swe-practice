"""Authored prose, reflowed to the width it is shown at.

**A prompt's line breaks were the author's editor's, not the author's.** Every
prompt and most example explanations are YAML literal blocks (`|`), wrapped at
about eighty columns because that is where the source file wraps. The page
used to show them in a `pre`, on the argument that a prompt "is already
shaped" -- and in a panel wider than eighty mono columns that drew every
paragraph as a ragged column with half the panel empty beside it, and in a
narrower one broke each source line again, leaving a stub of two words at the
end of every one. A paragraph's shape is the panel's to decide.

**What *is* shaped is kept exactly**, and the rule for telling the two apart is
the one the library already follows rather than one invented here. A fenced
block (```) is kept verbatim -- that is where the 43 drawings, query plans and
transcripts live. So is an unfenced block with an indented or column-aligned
line, which is how an explanation draws a tree. A run of `-`, `*` or `1.`
lines is a list, with its indented continuation lines joined into the item.
Everything else is a paragraph, and its lines are joined with a space.

**Not a markdown library**, which was the alternative, and the reason is what
it would add rather than what it costs to install. CommonMark would also give
headings, links, emphasis by underscore and raw HTML -- and a prompt that says
`__init__` or `a_b` would start rendering italics nobody wrote. The library
uses three inline marks, `code`, **bold** and *emphasis*, so those three are
the ones honoured, and only after the text is escaped.

The result is `Markup`, like the charts', so no template needs `| safe` and the
escaping decision stays where the escaping happens.
"""

from __future__ import annotations

import re
from typing import Final

from markupsafe import Markup, escape

__all__ = ["render_inline", "render_prose", "unclosed_fences"]

# The quiz sheet's rule (`domain/quiz/sheet.py`), so the two places that read a
# fence agree: three or more backticks or tildes, closed by a run of the same
# character at least as long with nothing after it. A longer fence is how a
# prompt shows a fenced block inside one.
_FENCE: Final = re.compile(r"^\s*(`{3,}|~{3,})")
# An item starts at the left margin. An indented one belongs to the item above
# it, as a nested list, which is what an author indenting it meant.
_ITEM: Final = re.compile(r"^(?:[-*]|(\d+)[.)])(\s+)(.*)$")
# A column, not a typo: a table or a log excerpt written without a fence still
# has to line up. Two spaces after a full stop is a typing habit, so two count
# only where no sentence ended; three count anywhere.
_ALIGNED: Final = re.compile(r"[^\s.!?:;,] {2,}\S|\S {3,}\S")
# `**` and `*` open only where a word does not run into them, so `10**5` and
# `2 * 3` -- both all over the constraints -- stay arithmetic.
_INLINE: Final = re.compile(
    r"`([^`\n]+)`"
    r"|(?<![\w*])\*\*(?!\s)(.+?)(?<!\s)\*\*(?![\w*])"
    r"|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"
)


def render_prose(text: str | None) -> Markup:
    """`text` as paragraphs, lists and verbatim blocks, ready for a page."""
    if not text:
        return Markup("")
    lines = text.strip("\n").splitlines()
    parts: list[str] = []
    block: list[str] = []

    def flush() -> None:
        if block:
            parts.append(_render_block(block))
            block.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        opener = _FENCE.match(line)
        closing = _closing_fence(lines, index, opener.group(1)) if opener else None
        if closing is not None:
            flush()
            parts.append(_verbatim(lines[index + 1 : closing]))
            index = closing
        elif not line.strip():
            flush()
        else:
            # An opening fence that never closes is text. Swallowing the rest
            # of the prompt into one unwrapped block would turn one missing
            # line into a page nobody can read, and the content suite holds
            # the library to closing every fence it opens.
            block.append(line)
        index += 1
    flush()
    # Every part was escaped where it was built, in `_inline` and `_verbatim`.
    return Markup("\n".join(parts))  # noqa: S704  (every value is escaped; see above)


def render_inline(text: str | None) -> Markup:
    """One line of text with its marks honoured, and nothing reflowed.

    For the short fields beside a prompt -- a parameter's description, a
    constraint, a hint -- which are authored in the same register and showed
    their backticks raw on the same panel as a prompt that did not.
    """
    if not text:
        return Markup("")
    return Markup(_inline(text))  # noqa: S704  (`_inline` escapes; see below)


def unclosed_fences(text: str | None) -> int:
    """How many fences in `text` open and never close: what a lint would ask."""
    lines = (text or "").splitlines()
    count = 0
    index = 0
    while index < len(lines):
        if opener := _FENCE.match(lines[index]):
            closing = _closing_fence(lines, index, opener.group(1))
            if closing is None:
                count += 1
            else:
                index = closing
        index += 1
    return count


def _closing_fence(lines: list[str], opening: int, opener: str) -> int | None:
    closer = re.compile(rf"^\s*{re.escape(opener[0])}{{{len(opener)},}}\s*$")
    for index in range(opening + 1, len(lines)):
        if closer.match(lines[index]):
            return index
    return None


def _render_block(lines: list[str]) -> str:
    """A block between blank lines: a list, verbatim, a paragraph, or a mix.

    **A list interrupts a paragraph only after a colon.** "It supports two
    operations:" with the list on the very next line is a sentence and then a
    list. But these breaks are the editor's, and a sentence wrapped at eighty
    columns can put `1. Then return.` or `- k` at the start of a line by
    accident; read as an item, that would cut the sentence in two.
    """
    for at, line in enumerate(lines):
        if _ITEM.match(line) and (at == 0 or lines[at - 1].rstrip().endswith(":")):
            if at == 0:
                return _render_list(lines)
            return _render_text(lines[:at]) + "\n" + _render_list(lines[at:])
    return _render_text(lines)


def _render_text(lines: list[str]) -> str:
    """Sentences, then whatever is drawn under them.

    The first indented or column-aligned line starts a verbatim run that goes
    to the end of the block, and the sentences above it are a paragraph of
    their own: "Example:" with the code on the next line must not be pulled
    into the `pre` and stop wrapping. Not split further than that, because a
    drawing's own lines need not all be indented -- the root of a tree can sit
    at the margin -- and a drawing cut into prose and `pre` is no drawing.
    """
    drawn = next(
        (
            at
            for at, line in enumerate(lines)
            if line[:1].isspace() or _ALIGNED.search(line)
        ),
        None,
    )
    if drawn is None:
        return f"<p>{_inline(' '.join(line.strip() for line in lines))}</p>"
    if drawn == 0:
        return _verbatim(lines)
    return _render_text(lines[:drawn]) + "\n" + _verbatim(lines[drawn:])


def _render_list(lines: list[str]) -> str:
    """A list, with each item's continuation lines joined onto it.

    **A continuation is a line indented to the item's text**, and is joined.
    Anything else under an item -- a nested item, or a line indented further,
    which is how a drawing sits under one -- is the start of that item's own
    content, rendered by the same rules after the item's indent is removed.
    Joining those too would flatten `- inner` into `outer - inner` and a tree
    into a run of slashes.

    Numbered when its first item is, and from that item's number, because
    "step 3" in a prompt is referred to by number elsewhere in it and a list
    resumed after a paragraph must not start again at 1.
    """
    # `_render_block` only sends a block whose first line is an item.
    first = _ITEM.match(lines[0])
    number = first.group(1) if first is not None else None
    items: list[tuple[list[str], list[str]]] = []
    indent = 0
    for line in lines:
        found = _ITEM.match(line)
        if found is not None:
            marker = len(line) - len(found.group(3))
            indent = marker
            items.append(([found.group(3)], []))
            continue
        text, nested = items[-1]
        stripped = line.strip()
        depth = len(line) - len(line.lstrip())
        if nested or depth > indent or _ITEM.match(stripped):
            nested.append(line[min(depth, indent) :])
        else:
            text.append(stripped)
    body = "".join(
        f"<li>{_inline(' '.join(text))}"
        + (f"\n{render_prose(chr(10).join(nested))}" if nested else "")
        + "</li>"
        for text, nested in items
    )
    if number is None:
        return f"<ul>{body}</ul>"
    start = int(number)
    return f'<ol start="{start}">{body}</ol>' if start != 1 else f"<ol>{body}</ol>"


def _verbatim(lines: list[str]) -> str:
    return f"<pre>{escape(chr(10).join(lines))}</pre>"


def _inline(text: str) -> str:
    """Escape `text`, then honour the three marks the library writes."""
    out: list[str] = []
    last = 0
    for found in _INLINE.finditer(text):
        out.append(str(escape(text[last : found.start()])))
        code, strong, emphasis = found.groups()
        if code is not None:
            out.append(f"<code>{escape(code)}</code>")
        elif strong is not None:
            out.append(f"<strong>{_inline(strong)}</strong>")
        else:
            out.append(f"<em>{_inline(emphasis)}</em>")
        last = found.end()
    out.append(str(escape(text[last:])))
    return "".join(out)
