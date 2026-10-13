"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import hamming_distance


def by_strings(a: int, b: int) -> int:
    """Write both numbers out in binary at the same width and compare."""
    width = max(a.bit_length(), b.bit_length(), 1)
    return sum(x != y for x, y in zip(f"{a:0{width}b}", f"{b:0{width}b}", strict=True))


def test_counts_the_differing_positions() -> None:
    """Counts two differing bits between 1 and 4."""
    assert hamming_distance(1, 4) == 2


def test_equal_numbers_differ_nowhere() -> None:
    """Returns 0 when the two numbers are the same."""
    assert hamming_distance(7, 7) == 0
    assert hamming_distance(0, 0) == 0


def test_counts_against_zero() -> None:
    """Counts every set bit when the other number is zero."""
    assert hamming_distance(0, 255) == 8
    assert hamming_distance(255, 0) == 8


def test_does_not_count_bits_that_are_set_in_both() -> None:
    """Ignores positions where both numbers hold a 1."""
    assert hamming_distance(0b1110, 0b0111) == 2
    assert hamming_distance(0b1111, 0b1111) == 0


def test_pads_the_shorter_number_with_zeros() -> None:
    """Counts the high bits of the wider number against zeros."""
    assert hamming_distance(1, 1 << 40) == 2


def test_agrees_with_comparing_binary_strings() -> None:
    """Matches a digit-by-digit comparison for every pair in 0..63."""
    for a in range(64):
        for b in range(64):
            assert hamming_distance(a, b) == by_strings(a, b), (a, b)


def test_handles_numbers_wider_than_a_machine_word() -> None:
    """Counts differences across a thousand bits."""
    ones = (1 << 1000) - 1

    assert hamming_distance(ones, 0) == 1000
    assert hamming_distance(ones, ones >> 1) == 1
    assert hamming_distance(1 << 1500, 1) == 2


def test_returns_an_int() -> None:
    """Returns an int rather than a bool."""
    assert type(hamming_distance(1, 0)) is int
