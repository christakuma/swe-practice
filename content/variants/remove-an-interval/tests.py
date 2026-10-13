"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, pairwise

from solution import remove


def cells(intervals: list[tuple[int, int]]) -> set[int]:
    """The unit cells a list of half-open intervals covers."""
    return {cell for start, end in intervals for cell in range(start, end)}


def test_trims_and_drops() -> None:
    """Trims the intervals at each edge and drops the one in the middle."""
    assert remove([(0, 2), (3, 4), (5, 7)], (1, 6)) == [(0, 1), (6, 7)]


def test_splits_an_interval_in_two() -> None:
    """Splits an interval that the removal falls inside."""
    assert remove([(0, 5)], (2, 3)) == [(0, 2), (3, 5)]


def test_leaves_intervals_it_only_touches() -> None:
    """Changes nothing when the removal only touches its neighbours."""
    assert remove([(0, 2), (5, 7)], (2, 5)) == [(0, 2), (5, 7)]


def test_never_returns_an_empty_interval() -> None:
    """Leaves no zero-length piece when an edge lines up exactly."""
    assert remove([(0, 5)], (0, 3)) == [(3, 5)]
    assert remove([(0, 5)], (3, 5)) == [(0, 3)]
    assert remove([(0, 5)], (0, 5)) == []


def test_handles_nothing_to_remove_from() -> None:
    """Returns an empty list for an empty list."""
    assert remove([], (1, 2)) == []


def test_agrees_with_removing_cell_by_cell() -> None:
    """Covers exactly the right cells, for every small list and every removal.

    Every list of up to three disjoint intervals with endpoints in 0..6,
    against every removal in the same range.
    """
    spans = [(start, end) for start, end in combinations(range(7), 2)]
    for size in range(4):
        for chosen in combinations(spans, size):
            if any(a[1] > b[0] for a, b in pairwise(chosen)):
                continue
            intervals = list(chosen)
            for gone in spans:
                result = remove(list(intervals), gone)
                expected = cells(intervals) - cells([gone])
                assert cells(result) == expected, (intervals, gone)
                assert all(start < end for start, end in result)
                assert result == sorted(result)
                assert len(result) <= len(intervals) + 1


def test_leaves_the_list_alone() -> None:
    """Does not modify the caller's list."""
    intervals = [(0, 5)]

    remove(intervals, (2, 3))

    assert intervals == [(0, 5)]


def test_removes_from_a_hundred_thousand_intervals() -> None:
    """Handles a hundred thousand intervals within the time limit."""
    intervals = [(3 * index, 3 * index + 2) for index in range(100_000)]

    result = remove(intervals, (4, 299_996))

    assert result == [(0, 2), (3, 4), (299_997, 299_999)]
