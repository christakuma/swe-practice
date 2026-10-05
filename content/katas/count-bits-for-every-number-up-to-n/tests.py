"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import count_bits_up_to


def test_handles_zero() -> None:
    """Returns a single zero for an input of zero."""
    assert count_bits_up_to(0) == [0]


def test_handles_one() -> None:
    """Returns the first two entries."""
    assert count_bits_up_to(1) == [0, 1]


def test_handles_the_worked_example() -> None:
    """Returns the counts up to five."""
    assert count_bits_up_to(5) == [0, 1, 1, 2, 1, 2]


def test_returns_one_entry_more_than_n() -> None:
    """Returns a list of length n + 1, because the range is inclusive.

    Off-by-one here is the most common wrong answer: a list of length n that
    stops at n - 1 agrees with the expected values everywhere it exists.
    """
    assert len(count_bits_up_to(10)) == 11
    assert len(count_bits_up_to(0)) == 1


def test_agrees_with_a_direct_count_across_a_wide_range() -> None:
    """Matches a direct reading of each number's binary string up to 1000."""
    expected = [bin(value).count("1") for value in range(1_001)]

    assert count_bits_up_to(1_000) == expected


def test_marks_powers_of_two_as_a_single_bit() -> None:
    """Gives every power of two a count of one."""
    counts = count_bits_up_to(600)

    for power in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512):
        assert counts[power] == 1, power


def test_marks_values_one_below_a_power_of_two_as_a_full_run() -> None:
    """Gives 2**k - 1 a count of k, because every bit below k is set."""
    counts = count_bits_up_to(300)

    for k in range(1, 9):
        assert counts[(1 << k) - 1] == k, k


def test_counts_the_boundary_at_a_new_bit_width() -> None:
    """Handles the step where a number gains a bit.

    255 is eight ones and 256 is a single one. A recurrence that reads the
    table at the wrong offset tends to carry the run across this boundary.
    """
    counts = count_bits_up_to(257)

    assert counts[255] == 8
    assert counts[256] == 1
    assert counts[257] == 2


def test_handles_a_large_range_in_linear_time() -> None:
    """Fills a table of a million entries within the time limit.

    Counting each number's bits independently is O(n log n) -- about twenty
    million bit reads here, against one million constant-time steps for the
    recurrence.
    """
    counts = count_bits_up_to(1_000_000)

    assert len(counts) == 1_000_001
    assert counts[1_000_000] == bin(1_000_000).count("1")
    assert counts[999_999] == bin(999_999).count("1")


def test_returns_plain_integers() -> None:
    """Returns ints, not booleans or another numeric type."""
    counts = count_bits_up_to(4)

    assert all(type(count) is int for count in counts)
