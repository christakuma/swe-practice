"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import largest_rectangle


def by_trying_every_span(heights: list[int]) -> int:
    best = 0
    for start in range(len(heights)):
        lowest = heights[start]
        for end in range(start, len(heights)):
            lowest = min(lowest, heights[end])
            best = max(best, lowest * (end - start + 1))
    return best


def test_finds_a_rectangle_across_two_tall_bars() -> None:
    """Spans adjacent bars at the height of the shorter one."""
    assert largest_rectangle([2, 1, 5, 6, 2, 3]) == 10


def test_a_single_tall_bar_can_be_the_answer() -> None:
    """Returns one bar's height when nothing wider is larger."""
    assert largest_rectangle([1, 8, 1]) == 8
    assert largest_rectangle([7]) == 7


def test_a_wide_low_rectangle_can_be_the_answer() -> None:
    """Spans every bar at the height of the shortest when that is largest."""
    assert largest_rectangle([3, 3, 3]) == 9
    assert largest_rectangle([2, 4, 2, 4, 2]) == 10


def test_the_bars_in_between_limit_the_height() -> None:
    """Does not use the two end bars' height across a shorter bar between them.

    As a container, the two 9s would hold 9 x 2. Under solid bars the 1 in
    the middle caps anything that spans it at height 1.
    """
    assert largest_rectangle([9, 1, 9]) == 9
    assert largest_rectangle([5, 5, 1, 5, 5]) == 10


def test_no_bars_hold_nothing() -> None:
    """Returns 0 for an empty list."""
    assert largest_rectangle([]) == 0


def test_bars_of_height_zero_split_the_row() -> None:
    """Treats a zero-height bar as a gap no rectangle can cross."""
    assert largest_rectangle([0]) == 0
    assert largest_rectangle([2, 2, 0, 2, 2, 2]) == 6
    assert largest_rectangle([0, 0, 0]) == 0


def test_measures_bars_that_never_meet_a_shorter_one() -> None:
    """Counts rectangles under bars still waiting when the list ends.

    In a rising row nothing ever arrives that is shorter, so every bar's
    rectangle runs to the end of the list and is measured only when the list
    runs out.
    """
    assert largest_rectangle([1, 2, 3, 4, 5]) == 9
    assert largest_rectangle([2, 4]) == 4


def test_handles_a_falling_row() -> None:
    """Measures each bar as soon as the next, shorter one arrives."""
    assert largest_rectangle([5, 4, 3, 2, 1]) == 9


def test_equal_bars_extend_through_each_other() -> None:
    """Lets a rectangle run across neighbouring bars of the same height."""
    assert largest_rectangle([4, 4, 4, 4]) == 16
    assert largest_rectangle([1, 3, 3, 3, 1]) == 9


def test_agrees_with_trying_every_span() -> None:
    """Matches an exhaustive search for every short row of bars.

    Every row of up to seven bars with heights drawn from 0..4.
    """
    for size in range(8):
        for chosen in product(range(5), repeat=size):
            heights = list(chosen)
            assert largest_rectangle(heights) == by_trying_every_span(heights), heights


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given, or leave a sentinel behind."""
    heights = [2, 1, 2]

    largest_rectangle(heights)

    assert heights == [2, 1, 2]


def test_handles_a_hundred_thousand_bars() -> None:
    """Handles a hundred thousand bars within the time limit.

    A staircase rising by one each bar. The best rectangle under a staircase
    1..n uses the upper half: bars n/2 + 1 to n at height n/2 + 1. Trying
    every pair of ends is five thousand million steps.
    """
    size = 100_000
    rising = list(range(1, size + 1))

    assert largest_rectangle(rising) == (size // 2) * (size // 2 + 1)
    assert largest_rectangle(rising[::-1]) == (size // 2) * (size // 2 + 1)
    assert largest_rectangle([7] * size) == 7 * size
