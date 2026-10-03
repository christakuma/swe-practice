"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import longest_increasing


def test_finds_a_subsequence_that_is_not_contiguous() -> None:
    """Skips over elements to find a longer run."""
    assert longest_increasing([10, 9, 2, 5, 3, 7, 101, 18]) == 4


def test_handles_an_already_sorted_list() -> None:
    """Returns the whole length when the list is already increasing."""
    assert longest_increasing([1, 2, 3, 4, 5]) == 5


def test_handles_a_descending_list() -> None:
    """Returns one when the list only ever decreases."""
    assert longest_increasing([5, 4, 3, 2, 1]) == 1


def test_is_strictly_increasing() -> None:
    """Counts a run of equal values as length one.

    This is where `bisect_left` versus `bisect_right` shows up: with the wrong
    one, each equal value appends a new tail and this returns 4.
    """
    assert longest_increasing([7, 7, 7, 7]) == 1


def test_handles_repeats_inside_a_longer_run() -> None:
    """Does not count a repeat as an increase."""
    assert longest_increasing([2, 2, 3, 3, 4]) == 3


def test_prefers_a_later_shorter_start() -> None:
    """Finds a run that begins after a false start.

    The leading 0 and 1 look promising and the answer runs 0, 1, 2, 3 using the
    *second* 0's position -- which is only reachable by keeping the smallest
    possible ending for each length.
    """
    assert longest_increasing([0, 1, 0, 3, 2, 3]) == 4


def test_handles_a_single_element() -> None:
    """Returns one for a single element."""
    assert longest_increasing([5]) == 1


def test_handles_an_empty_list() -> None:
    """Returns zero for no input."""
    assert longest_increasing([]) == 0


def test_handles_an_interleaved_list() -> None:
    """Finds the longest run in a list that rises and falls."""
    assert longest_increasing([3, 1, 4, 1, 5, 9, 2, 6]) == 4


def test_handles_a_long_list_quickly() -> None:
    """Solves a list far too long for the quadratic version.

    Four thousand elements: two ascending runs back to back, so the answer is
    two thousand. The O(n^2) version is sixteen million comparisons, which is
    borderline; the binary-search version is four thousand searches.
    """
    numbers = list(range(2_000)) + list(range(2_000))

    assert longest_increasing(numbers) == 2_000
