"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_balanced

PARTNER = {")": "(", "]": "[", "}": "{"}


def is_balanced(text: str) -> bool:
    stack = []
    for character in text:
        if character not in PARTNER:
            stack.append(character)
        elif not stack or stack.pop() != PARTNER[character]:
            return False
    return not stack


def by_trying_every_stretch(text: str) -> int:
    return max(
        (
            end - start
            for start in range(len(text))
            for end in range(start + 2, len(text) + 1, 2)
            if is_balanced(text[start:end])
        ),
        default=0,
    )


def test_a_balanced_string_is_its_own_longest_stretch() -> None:
    """Returns the full length when the whole string is balanced."""
    assert longest_balanced("()") == 2
    assert longest_balanced("([{}])") == 6
    assert longest_balanced("()[]{}") == 6


def test_finds_a_stretch_after_an_unclosed_opener() -> None:
    """Skips an opener that is never closed."""
    assert longest_balanced("(()") == 2
    assert longest_balanced("[[[]]") == 4


def test_finds_a_stretch_between_stray_closers() -> None:
    """Skips closers that have nothing to match."""
    assert longest_balanced(")()[]}") == 4
    assert longest_balanced("))()") == 2


def test_neighbouring_stretches_join() -> None:
    """Counts balanced stretches side by side as one."""
    assert longest_balanced("()()") == 4
    assert longest_balanced("(){}[]()") == 8
    assert longest_balanced(")()()(") == 4


def test_separated_stretches_do_not_join() -> None:
    """Does not add up stretches with an unmatched bracket between them."""
    assert longest_balanced("()(()") == 2
    assert longest_balanced("()](){}") == 4
    assert longest_balanced("(){()[]") == 4


def test_returns_zero_when_nothing_is_balanced() -> None:
    """Returns 0 for the empty string and for strings with no matching pair."""
    assert longest_balanced("") == 0
    assert longest_balanced("(((") == 0
    assert longest_balanced(")))") == 0
    assert longest_balanced(")(") == 0


def test_a_closer_must_be_the_right_kind() -> None:
    """Does not match an opener with a closer of a different kind."""
    assert longest_balanced("(]") == 0
    assert longest_balanced("([)]") == 0
    assert longest_balanced("{(})") == 0


def test_a_wrong_closer_cuts_off_everything_before_it() -> None:
    """Starts afresh after a closer of the wrong kind.

    In "(()]()" the "]" cannot be matched, so the opener at the very start
    can never be closed either, and the pairs on each side of the "]" stay
    separate.
    """
    assert longest_balanced("(()]()") == 2
    assert longest_balanced("[()]}()[]{}") == 6
    assert longest_balanced("({)}[]") == 2


def test_agrees_with_trying_every_stretch() -> None:
    """Matches an exhaustive search for every short string.

    Every string of up to eight round brackets, and every string of up to
    six characters over round and square brackets.
    """
    for alphabet, longest in (("()", 8), ("()[]", 6)):
        for size in range(longest + 1):
            for characters in product(alphabet, repeat=size):
                text = "".join(characters)
                assert longest_balanced(text) == by_trying_every_stretch(text), text


def test_handles_deep_nesting() -> None:
    """Handles brackets nested fifty thousand deep without recursing."""
    depth = 50_000

    assert longest_balanced("(" * depth + ")" * depth) == 2 * depth
    assert longest_balanced("[" * depth + "]" * (depth - 1)) == 2 * (depth - 1)
    assert longest_balanced("{" * depth + ")" + "}" * depth) == 0


def test_handles_a_long_string_of_short_stretches() -> None:
    """Handles a hundred thousand characters within the time limit.

    Pairs with a stray closer after every three of them, so no stretch is
    longer than six. Checking every stretch separately is thousands of
    millions of steps.
    """
    text = "()[]{})" * 14_000

    assert longest_balanced(text) == 6
    assert longest_balanced("()" * 50_000) == 100_000
