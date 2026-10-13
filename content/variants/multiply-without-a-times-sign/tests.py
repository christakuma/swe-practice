"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import INT_MAX, INT_MIN, multiply


def wrapped(a: int, b: int) -> int:
    """The product, wrapped into the signed 32-bit range by arithmetic."""
    return (a * b + 2**31) % 2**32 - 2**31


def test_multiplies_two_positives() -> None:
    """Multiplies two positive numbers."""
    assert multiply(6, 7) == 42
    assert multiply(123, 456) == 56088


def test_multiplies_by_zero_and_one() -> None:
    """Returns 0 for a zero operand and the other operand for a one."""
    assert multiply(0, 0) == 0
    assert multiply(0, 99) == 0
    assert multiply(99, 0) == 0
    assert multiply(1, 99) == 99
    assert multiply(99, 1) == 99


def test_handles_every_combination_of_signs() -> None:
    """Gives a negative product for mixed signs and a positive one for two negatives."""
    assert multiply(-4, 5) == -20
    assert multiply(4, -5) == -20
    assert multiply(-4, -5) == 20
    assert multiply(-1, -1) == 1


def test_wraps_a_product_that_is_too_large() -> None:
    """Keeps the low 32 bits of a product that overflows."""
    assert multiply(65536, 65536) == 0
    assert multiply(INT_MAX, 2) == -2
    assert multiply(INT_MAX, INT_MAX) == 1
    assert multiply(46341, 46341) == wrapped(46341, 46341)


def test_wraps_at_the_most_negative_value() -> None:
    """Handles INT_MIN, whose negation does not fit in the word."""
    assert multiply(INT_MIN, -1) == INT_MIN
    assert multiply(INT_MIN, 2) == 0
    assert multiply(INT_MIN, 3) == INT_MIN
    assert multiply(INT_MIN, INT_MIN) == 0


def test_agrees_with_wrapped_arithmetic() -> None:
    """Matches a wrapped reference for every pair in -40..40 and at the edges."""
    for a in range(-40, 41):
        for b in range(-40, 41):
            assert multiply(a, b) == wrapped(a, b), (a, b)
    edges = (INT_MIN, INT_MIN + 1, -65537, -1, 0, 1, 3, 65535, 1 << 30, INT_MAX)
    for a in edges:
        for b in edges:
            assert multiply(a, b) == wrapped(a, b), (a, b)


def test_stays_in_range() -> None:
    """Returns a result within the signed 32-bit range."""
    for a, b in ((INT_MIN, INT_MAX), (INT_MAX, INT_MAX), (123456789, 987654321)):
        assert INT_MIN <= multiply(a, b) <= INT_MAX


def test_does_not_count_up_to_the_multiplier() -> None:
    """Multiplies by numbers in the thousands of millions within the time limit.

    Two hundred products whose second factor is near 2**31. Adding the first
    factor that many times is hundreds of thousands of millions of additions;
    one row per bit is thirty-two.
    """
    for step in range(200):
        a = 1_000_003 + step
        b = INT_MAX - step
        assert multiply(a, b) == wrapped(a, b)
        assert multiply(b, a) == wrapped(b, a)
