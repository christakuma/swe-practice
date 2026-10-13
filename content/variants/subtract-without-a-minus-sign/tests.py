"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import INT_MAX, INT_MIN, subtract


def wrapped(a: int, b: int) -> int:
    """The difference, wrapped into the signed 32-bit range by arithmetic."""
    return (a - b + 2**31) % 2**32 - 2**31


def test_subtracts_a_smaller_number() -> None:
    """Returns a positive difference."""
    assert subtract(5, 3) == 2


def test_goes_below_zero() -> None:
    """Returns a negative difference."""
    assert subtract(3, 5) == -2
    assert subtract(0, 1) == -1


def test_handles_negative_operands() -> None:
    """Subtracts negative numbers in every combination."""
    assert subtract(7, -3) == 10
    assert subtract(-7, 3) == -10
    assert subtract(-7, -3) == -4


def test_returns_zero_for_equal_operands() -> None:
    """Returns 0 when the two numbers are equal."""
    assert subtract(123456, 123456) == 0
    assert subtract(INT_MIN, INT_MIN) == 0


def test_wraps_at_both_ends() -> None:
    """Wraps below INT_MIN and above INT_MAX."""
    assert subtract(INT_MIN, 1) == INT_MAX
    assert subtract(INT_MAX, -1) == INT_MIN
    assert subtract(0, INT_MIN) == INT_MIN


def test_agrees_with_wrapped_arithmetic() -> None:
    """Matches a wrapped reference for every pair in -70..70 and at the edges."""
    for a in range(-70, 71):
        for b in range(-70, 71):
            assert subtract(a, b) == wrapped(a, b), (a, b)
    edges = (INT_MIN, INT_MIN + 1, -1, 0, 1, INT_MAX - 1, INT_MAX, 1 << 30)
    for a in edges:
        for b in edges:
            assert subtract(a, b) == wrapped(a, b), (a, b)


def test_stays_in_range() -> None:
    """Returns a result within the signed 32-bit range."""
    for a, b in ((INT_MIN, INT_MAX), (INT_MAX, INT_MIN), (0, 0)):
        assert INT_MIN <= subtract(a, b) <= INT_MAX
