"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import count_subarrays


def test_counts_two_overlapping_slices() -> None:
    """Counts every slice, including ones that overlap."""
    assert count_subarrays([1, 1, 1], 2) == 2


def test_counts_a_slice_that_starts_at_the_beginning() -> None:
    """Counts a slice beginning at index zero.

    The case the `seen[0] = 1` base case exists for. Without it this returns 0.
    """
    assert count_subarrays([3], 3) == 1


def test_handles_negative_numbers() -> None:
    """Counts slices correctly when values can be negative.

    The three are [1, -1], [1, -1, 0] and [0]. A sliding window cannot find
    them: it relies on the sum growing as the window widens, and here widening
    from [1] to [1, -1] makes the sum smaller.
    """
    assert count_subarrays([1, -1, 0], 0) == 3


def test_counts_zero_sum_slices_made_of_zeroes() -> None:
    """Counts the slices of a run of zeros when the target is zero."""
    assert count_subarrays([0, 0, 0], 0) == 6


def test_finds_nothing_when_no_slice_matches() -> None:
    """Returns zero when no slice sums to the target."""
    assert count_subarrays([1, 2, 3], 7) == 0


def test_handles_an_empty_list() -> None:
    """Returns zero for no input."""
    assert count_subarrays([], 0) == 0


def test_counts_the_whole_list_as_a_slice() -> None:
    """Counts the whole list when it sums to the target."""
    assert count_subarrays([2, 4, 6], 12) == 1


def test_counts_several_separate_matches() -> None:
    """Counts matches that do not overlap."""
    assert count_subarrays([5, 1, 4, 5], 5) == 3


def test_handles_a_long_list_quickly() -> None:
    """Counts slices in a list far too long to try every slice.

    Twenty thousand ones with a target of two. Every adjacent pair matches, so
    the answer is 19,999 -- and there are two hundred million slices to try if
    you try them all.
    """
    size = 20_000

    assert count_subarrays([1] * size, 2) == size - 1
