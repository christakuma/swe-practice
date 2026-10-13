"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, combinations_with_replacement

from solution import most_valuable

type Interval = tuple[int, int, int]


def by_trying_every_selection(intervals: list[Interval]) -> int:
    """The best total over every subset in which no two intervals overlap."""
    best = 0
    for size in range(1, len(intervals) + 1):
        for chosen in combinations(intervals, size):
            clear = all(
                first[1] <= second[0] or second[1] <= first[0]
                for first, second in combinations(chosen, 2)
            )
            if clear:
                best = max(best, sum(value for _, _, value in chosen))
    return best


def test_keeps_the_more_valuable_of_two_that_overlap() -> None:
    """Chooses by value when two intervals cannot both be kept."""
    assert most_valuable([(0, 2, 1), (0, 3, 9)]) == 9
    assert most_valuable([(0, 2, 9), (0, 3, 1)]) == 9


def test_adds_up_intervals_that_do_not_overlap() -> None:
    """Keeps every interval when none of them overlap."""
    assert most_valuable([(0, 1, 2), (5, 6, 3), (2, 3, 4)]) == 9


def test_touching_intervals_can_both_be_kept() -> None:
    """Treats an interval that starts where another ends as compatible."""
    assert most_valuable([(1, 2, 3), (2, 3, 4)]) == 7
    assert most_valuable([(2, 3, 4), (1, 2, 3), (3, 4, 5)]) == 12


def test_one_valuable_interval_beats_several_small_ones() -> None:
    """Gives up three intervals to keep one that is worth more than all of them."""
    assert most_valuable([(0, 1, 2), (1, 2, 2), (2, 3, 2), (0, 3, 7)]) == 7


def test_several_small_intervals_beat_one_valuable_one() -> None:
    """Gives up the single most valuable interval when the others total more."""
    assert most_valuable([(0, 1, 3), (1, 2, 3), (2, 3, 3), (0, 3, 8)]) == 9


def test_the_middle_interval_is_not_always_the_one_to_drop() -> None:
    """Weighs a middle interval against both of the neighbours it blocks."""
    assert most_valuable([(1, 3, 5), (2, 5, 6), (4, 6, 5), (6, 7, 4)]) == 14
    assert most_valuable([(1, 3, 5), (2, 5, 11), (4, 6, 5)]) == 11


def test_identical_intervals_overlap() -> None:
    """Keeps only one of two copies of the same interval."""
    assert most_valuable([(1, 4, 5), (1, 4, 5)]) == 5
    assert most_valuable([(1, 4, 5), (1, 4, 6)]) == 6


def test_handles_none_and_one() -> None:
    """Returns 0 for no intervals and the value of a single one."""
    assert most_valuable([]) == 0
    assert most_valuable([(-5, 5, 42)]) == 42


def test_handles_negative_coordinates() -> None:
    """Handles intervals that lie below zero and across it."""
    assert most_valuable([(-10, -5, 1), (-5, 0, 2), (-7, 3, 2)]) == 3


def test_agrees_with_trying_every_selection() -> None:
    """Matches an exhaustive search for every small set of intervals.

    Every multiset of up to three intervals with ends in 0..4 and values in
    1, 2, 4, and a spread of sets of four.
    """
    shapes = [(start, end) for start, end in combinations(range(5), 2)]
    pool = [(start, end, value) for start, end in shapes for value in (1, 2, 4)]
    for size in range(1, 4):
        for chosen in combinations_with_replacement(pool, size):
            intervals = list(chosen)
            expected = by_trying_every_selection(intervals)
            assert most_valuable(intervals) == expected, intervals
    for chosen in combinations(pool[::2], 4):
        intervals = list(chosen)
        assert most_valuable(intervals) == by_trying_every_selection(intervals)


def test_leaves_the_list_alone() -> None:
    """Does not reorder or modify the list it was given."""
    intervals = [(4, 6, 1), (0, 2, 5), (1, 5, 3)]

    most_valuable(intervals)

    assert intervals == [(4, 6, 1), (0, 2, 5), (1, 5, 3)]


def test_handles_a_hundred_thousand_intervals() -> None:
    """Handles 100,000 intervals within the time limit.

    Fifty thousand unit intervals laid end to end, each worth 3, and over
    every adjacent pair of them one interval worth 5. Looking back through
    every earlier interval for each one is thousands of millions of steps.
    """
    count = 50_000
    units = [(index, index + 1, 3) for index in range(count)]
    pairs = [(index, index + 2, 5) for index in range(0, count, 2)]

    assert most_valuable(units + pairs) == 3 * count
    assert most_valuable([*pairs, (0, count, 1)]) == 5 * (count // 2)
