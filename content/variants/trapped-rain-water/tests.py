"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import trapped_water


def bar_by_bar(heights: list[int]) -> int:
    """For each bar, look left and right for the tallest and take the lower."""
    return sum(
        max(min(max(heights[: index + 1]), max(heights[index:])) - height, 0)
        for index, height in enumerate(heights)
    )


def test_fills_the_worked_example() -> None:
    """Traps six units in the worked example."""
    assert trapped_water([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6


def test_fills_a_dip_to_its_lower_side() -> None:
    """Fills a dip to the height of the lower wall."""
    assert trapped_water([3, 0, 2]) == 2
    assert trapped_water([2, 0, 3]) == 2


def test_holds_nothing_on_a_slope() -> None:
    """Traps nothing when the bars only rise or only fall."""
    assert trapped_water([1, 2, 3]) == 0
    assert trapped_water([3, 2, 1]) == 0


def test_bars_take_up_room() -> None:
    """Subtracts the bars standing in the water.

    The container between the two 4s would hold 12. A bar of height 3 in the
    middle of it leaves 4 + 1 + 4.
    """
    assert trapped_water([4, 0, 3, 0, 4]) == 9


def test_handles_short_lists() -> None:
    """Traps nothing with fewer than three bars."""
    assert trapped_water([]) == 0
    assert trapped_water([5]) == 0
    assert trapped_water([5, 5]) == 0


def test_agrees_with_measuring_bar_by_bar() -> None:
    """Matches a bar-by-bar measurement for every list up to length seven."""
    for length in range(8):
        for chosen in product(range(4), repeat=length):
            heights = list(chosen)
            assert trapped_water(heights) == bar_by_bar(heights), heights


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    heights = [3, 0, 2]

    trapped_water(heights)

    assert heights == [3, 0, 2]


def test_handles_a_million_bars() -> None:
    """Handles a million bars within the time limit.

    A peak: rising for half a million bars and falling again, which holds
    nothing. Then a basin a million bars wide. Looking left and right from
    every bar is a trillion comparisons.
    """
    half = 500_000
    heights = list(range(1, half + 1)) + list(range(half, 0, -1))

    assert trapped_water(heights) == 0
    assert trapped_water([half, *([0] * (2 * half)), half]) == 2 * half * half
