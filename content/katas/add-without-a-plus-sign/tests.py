"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import INT_MAX, INT_MIN, MASK, add

WORD = MASK + 1


def reference(a: int, b: int) -> int:
    """Wrap `a + b` into a signed 32-bit word -- using the banned operator.

    An independent oracle with different failure modes from any shift-and-mask
    implementation, which is exactly why it is allowed to cheat.
    """
    total = (a + b) & MASK
    return total if total <= INT_MAX else total - WORD


def test_adds_two_positives() -> None:
    """Adds two positive numbers."""
    assert add(1, 2) == 3
    assert add(123, 456) == 579


def test_adds_zero() -> None:
    """Returns the other operand when one is zero."""
    assert add(0, 0) == 0
    assert add(0, 42) == 42
    assert add(42, 0) == 42


def test_adds_a_negative_to_a_positive() -> None:
    """Handles mixed signs, including a result of zero.

    Negative inputs are where an unmasked loop hangs rather than fails: the
    Python representation of -1 has no end, so the carries never run out.
    """
    assert add(-1, 1) == 0
    assert add(-5, 3) == -2
    assert add(3, -5) == -2


def test_adds_two_negatives() -> None:
    """Adds two negative numbers."""
    assert add(-2, -3) == -5
    assert add(-1, -1) == -2


def test_carries_across_a_long_run_of_ones() -> None:
    """Propagates a carry through many columns at once.

    One round of carry handling is not enough; this needs several, and a
    solution that computes the carry-less sum and the carries but adds them
    only once returns 0 here.
    """
    assert add(0b0111_1111, 1) == 0b1000_0000
    assert add(65_535, 1) == 65_536


def test_wraps_on_positive_overflow() -> None:
    """Wraps past INT_MAX instead of growing the number.

    Python would happily return 2147483648. A 32-bit word cannot, and the
    masking is what makes the difference visible.
    """
    assert add(INT_MAX, 1) == INT_MIN
    assert add(INT_MAX, INT_MAX) == -2


def test_wraps_on_negative_overflow() -> None:
    """Wraps below INT_MIN."""
    assert add(INT_MIN, -1) == INT_MAX
    assert add(INT_MIN, INT_MIN) == 0


def test_handles_the_extremes_together() -> None:
    """Adds the two ends of the range."""
    assert add(INT_MAX, INT_MIN) == -1
    assert add(INT_MIN, 0) == INT_MIN
    assert add(INT_MAX, 0) == INT_MAX


def test_agrees_with_a_reference_across_every_small_pair() -> None:
    """Matches a wrapped reference sum for every pair in -120..120.

    Nearly sixty thousand pairs, covering every sign combination and every
    carry length that fits. A sign-handling special case that happens to work
    on the hand-picked cases above does not survive this.
    """
    for a, b in product(range(-120, 121), repeat=2):
        assert add(a, b) == reference(a, b), (a, b)


def test_agrees_with_a_reference_near_the_boundaries() -> None:
    """Matches the reference around INT_MIN, INT_MAX and the sign bit."""
    edges = (
        INT_MIN,
        INT_MIN + 1,
        INT_MIN + 2,
        -65_537,
        -65_536,
        -1,
        0,
        1,
        65_535,
        65_536,
        INT_MAX - 2,
        INT_MAX - 1,
        INT_MAX,
    )
    for a, b in product(edges, repeat=2):
        assert add(a, b) == reference(a, b), (a, b)


def test_returns_a_value_inside_the_word() -> None:
    """Returns a result within the signed 32-bit range."""
    for a, b in product((INT_MIN, -1, 0, 1, INT_MAX), repeat=2):
        assert INT_MIN <= add(a, b) <= INT_MAX, (a, b)
