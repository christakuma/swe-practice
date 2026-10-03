"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import merge_intervals


def test_merges_two_overlapping_intervals() -> None:
    """Merges intervals that overlap."""
    assert merge_intervals([(1, 4), (2, 6)]) == [(1, 6)]


def test_leaves_separate_intervals_alone() -> None:
    """Keeps intervals that do not touch as separate intervals."""
    assert merge_intervals([(1, 2), (5, 7)]) == [(1, 2), (5, 7)]


def test_sorts_the_result_by_start() -> None:
    """Handles input in any order and returns the result sorted."""
    assert merge_intervals([(8, 10), (1, 3), (2, 6)]) == [(1, 6), (8, 10)]


def test_merges_intervals_that_only_touch() -> None:
    """Merges intervals that meet at a single point.

    These are closed intervals, so 3 is in both (1, 3) and (3, 5). The
    comparison has to be `start <= last_end`, not `<`.
    """
    assert merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]


def test_swallows_an_interval_contained_in_another() -> None:
    """Keeps the wider end when one interval contains another.

    A solution that extends to the new interval's end rather than the maximum
    returns (1, 4) here, and passes every test where the intervals are ragged.
    """
    assert merge_intervals([(1, 10), (2, 4)]) == [(1, 10)]


def test_merges_a_chain_of_overlaps() -> None:
    """Merges a run where each interval overlaps only the previous one."""
    assert merge_intervals([(1, 3), (2, 5), (4, 8), (7, 9)]) == [(1, 9)]


def test_handles_a_single_interval() -> None:
    """Returns one interval unchanged."""
    assert merge_intervals([(3, 7)]) == [(3, 7)]


def test_handles_no_intervals() -> None:
    """Returns nothing for no intervals."""
    assert merge_intervals([]) == []


def test_handles_zero_length_intervals() -> None:
    """Collapses duplicate single-point intervals without joining distant ones.

    Two copies of (2, 2) are one interval; (5, 5) is somewhere else entirely.
    A solution that merges whenever the starts are sorted -- without comparing
    against the previous end at all -- returns a single (2, 5) here.
    """
    assert merge_intervals([(2, 2), (2, 2), (5, 5)]) == [(2, 2), (5, 5)]


def test_merges_many_intervals_quickly() -> None:
    """Merges a list far too long to compare every pair.

    Ten thousand intervals forming one chain. Comparing every pair is a hundred
    million comparisons; sorting then one pass is ten thousand log ten
    thousand.
    """
    intervals = [(index, index + 2) for index in range(10_000)]

    assert merge_intervals(intervals) == [(0, 10_001)]
