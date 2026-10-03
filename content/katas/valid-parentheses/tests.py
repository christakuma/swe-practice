"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import is_balanced


def test_accepts_a_simple_pair() -> None:
    """Accepts one opener closed by its partner."""
    assert is_balanced("()") is True


def test_accepts_nested_brackets_of_different_kinds() -> None:
    """Accepts correctly nested brackets of mixed kinds."""
    assert is_balanced("{[()]}") is True


def test_accepts_brackets_side_by_side() -> None:
    """Accepts several closed groups in sequence."""
    assert is_balanced("()[]{}") is True


def test_rejects_crossed_brackets() -> None:
    """Rejects brackets that overlap instead of nesting.

    The case that rules out counting. Every kind appears exactly once as an
    opener and once as a closer, so any count-based solution says yes.
    """
    assert is_balanced("([)]") is False


def test_rejects_an_unclosed_opener() -> None:
    """Rejects an opener that is never closed.

    A solution that only checks each closer against the stack top -- and never
    checks that the stack is empty at the end -- says yes here.
    """
    assert is_balanced("((") is False


def test_rejects_a_closer_with_nothing_open() -> None:
    """Rejects a closer that arrives first."""
    assert is_balanced(")(") is False


def test_rejects_a_mismatched_pair() -> None:
    """Rejects an opener closed by the wrong kind of bracket."""
    assert is_balanced("(]") is False


def test_accepts_an_empty_string() -> None:
    """Accepts no brackets at all: nothing is unclosed."""
    assert is_balanced("") is True


def test_handles_deep_nesting_quickly() -> None:
    """Handles nesting far deeper than a recursive scan would enjoy.

    Fifty thousand openers then fifty thousand closers. A solution that
    repeatedly scans for the innermost pair and removes it is quadratic; a
    stack is one pass.
    """
    depth = 50_000

    assert is_balanced("(" * depth + ")" * depth) is True
