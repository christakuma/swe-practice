"""The prose filter: a prompt's paragraphs fill the panel, its drawings do not move.

The defect this replaced was a `pre` around the whole prompt, which kept the
source file's eighty-column breaks at every width. So the first assertion is
the one that failed then -- a hard-wrapped paragraph comes out as one line --
and the rest are about what must *not* be reflowed while doing it.
"""

from __future__ import annotations

from practice.interface.web.prose import render_inline, render_prose, unclosed_fences


def test_a_hard_wrapped_paragraph_is_one_paragraph() -> None:
    text = "Build a word store supporting\ntwo operations, and nothing\nelse.\n"

    assert (
        render_prose(text)
        == "<p>Build a word store supporting two operations, and nothing else.</p>"
    )


def test_a_blank_line_separates_paragraphs() -> None:
    assert render_prose("One.\n\nTwo.") == "<p>One.</p>\n<p>Two.</p>"


def test_a_fenced_block_is_kept_exactly_blank_lines_and_all() -> None:
    text = "Before:\n\n```\n  a   b\n\n    c\n```\nAfter."

    assert (
        render_prose(text)
        == "<p>Before:</p>\n<pre>  a   b\n\n    c</pre>\n<p>After.</p>"
    )


def test_an_indented_drawing_is_kept_without_a_fence() -> None:
    """How every tree in an example's explanation is drawn."""
    text = "Both trees are\n\n      1\n     / \\\n    2   3"

    assert (
        render_prose(text)
        == "<p>Both trees are</p>\n<pre>      1\n     / \\\n    2   3</pre>"
    )


def test_a_list_joins_each_item_s_continuation_lines() -> None:
    text = (
        "Two operations:\n\n"
        "- `add(word)` stores it.\n"
        "- `search(p)` asks, where\n"
        "  a dot is any character."
    )

    assert render_prose(text) == (
        "<p>Two operations:</p>\n"
        "<ul><li><code>add(word)</code> stores it.</li>"
        "<li><code>search(p)</code> asks, where a dot is any character.</li></ul>"
    )


def test_a_list_straight_after_its_sentence_is_still_a_list() -> None:
    assert (
        render_prose("Steps:\n1. one\n2. two")
        == "<p>Steps:</p>\n<ol><li>one</li><li>two</li></ol>"
    )


def test_the_three_inline_marks_and_no_others() -> None:
    """`__init__` and `a_b` are names, not emphasis; `2 * 3 * 4` is arithmetic."""
    text = "**Exactly one** *other* `x*y` __init__ a_b 2 * 3 * 4"

    assert render_prose(text) == (
        "<p><strong>Exactly one</strong> <em>other</em> <code>x*y</code>"
        " __init__ a_b 2 * 3 * 4</p>"
    )


def test_everything_is_escaped_before_any_mark_is_honoured() -> None:
    text = "a < b && `<script>` **<b>x</b>**\n\n```\n<i>\n```"

    out = render_prose(text)

    assert "<script>" not in out
    assert "<b>x</b>" not in out
    assert out == (
        "<p>a &lt; b &amp;&amp; <code>&lt;script&gt;</code>"
        " <strong>&lt;b&gt;x&lt;/b&gt;</strong></p>\n"
        "<pre>&lt;i&gt;</pre>"
    )


def test_nothing_renders_nothing() -> None:
    assert render_prose("") == ""
    assert render_prose(None) == ""


# --- the four traps a review found ---------------------------------------------


def test_two_spaces_after_a_full_stop_is_still_a_paragraph() -> None:
    """A typing habit, not a column: the paragraph must still reflow."""
    text = "Return them in order.  Then\nstop."

    assert render_prose(text) == "<p>Return them in order.  Then stop.</p>"


def test_a_column_is_still_kept_verbatim() -> None:
    text = "IMAGE   STATUS\nweb     Exited (137)"

    assert render_prose(text).startswith("<pre>IMAGE   STATUS")


def test_an_indented_item_is_a_nested_list() -> None:
    assert render_prose("- outer\n  - inner\n  - other\n- next") == (
        "<ul><li>outer\n<ul><li>inner</li><li>other</li></ul></li><li>next</li></ul>"
    )


def test_a_drawing_under_an_item_is_kept_verbatim() -> None:
    tree = "\n".join(["      1", "     / \\", "    2   3"])
    # A blank line ends the list block, so the drawing is its own `pre` ...
    assert f"<pre>{tree}</pre>" in render_prose(f"- a tree:\n\n{tree}")
    # ... and indented straight under the item, it is the item's content,
    # moved left by the item's indent and otherwise exactly as drawn.
    under = "\n".join(["    1", "   / \\", "  2   3"])
    assert render_prose(f"- a tree:\n{tree}") == (
        f"<ul><li>a tree:\n<pre>{under}</pre></li></ul>"
    )


def test_a_numbered_list_resumed_after_a_paragraph_keeps_its_number() -> None:
    out = render_prose("1. a\n2. b\n\nA note.\n\n3. c")

    assert out == (
        '<ol><li>a</li><li>b</li></ol>\n<p>A note.</p>\n<ol start="3"><li>c</li></ol>'
    )


def test_an_unclosed_fence_is_text_and_the_rest_still_reflows() -> None:
    text = "```\nfirst\nline\n\nlater\nparagraph"

    assert render_prose(text) == "<p>``` first line</p>\n<p>later paragraph</p>"
    assert unclosed_fences(text) == 1
    assert unclosed_fences("```\nx\n```\n```\ny\n```") == 0


def test_arithmetic_in_a_constraint_is_not_bold() -> None:
    """`10**5` and `10**9` in one line would otherwise bold `5 <= n <= 10`."""
    text = "1 <= len(nums) <= 10**5 and -10**9 <= nums[i] <= 10**9"

    assert render_inline(text) == text.replace("<", "&lt;")


def test_inline_honours_the_marks_without_wrapping_in_a_paragraph() -> None:
    assert render_inline("the word, with `.` for **any** one") == (
        "the word, with <code>.</code> for <strong>any</strong> one"
    )
    assert render_inline(None) == ""


# --- the second review ---------------------------------------------------------


def test_a_longer_fence_holds_a_shorter_one() -> None:
    inner = "\n".join(["```", "inner", "```"])

    assert render_prose(f"````\n{inner}\n````") == f"<pre>{inner}</pre>"
    # A shorter run does not close a longer fence, so the content test flags it.
    assert unclosed_fences("````\nx\n```") > 0


def test_a_tilde_fence_is_a_fence() -> None:
    assert render_prose("~~~\nx  =  1\nplain\n~~~") == "<pre>x  =  1\nplain</pre>"


def test_a_wrapped_line_that_starts_with_a_number_is_not_a_list() -> None:
    """Only a colon lets a list break into a sentence."""
    text = "values from 0 to\n1. Then return them\n- k at most."

    assert render_prose(text) == (
        "<p>values from 0 to 1. Then return them - k at most.</p>"
    )


def test_the_sentence_above_a_drawing_still_wraps() -> None:
    assert render_prose("Example:\n    f(1) == 2") == (
        "<p>Example:</p>\n<pre>    f(1) == 2</pre>"
    )
