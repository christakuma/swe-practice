"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import largest_island


def by_merging(grid: list[list[int]]) -> int:
    """Start with every land cell alone and merge neighbours until none are left."""
    groups = [
        {(top, left)}
        for top, row in enumerate(grid)
        for left, cell in enumerate(row)
        if cell == 1
    ]
    merged = True
    while merged:
        merged = False
        for first in range(len(groups)):
            for second in range(first + 1, len(groups)):
                touching = any(
                    abs(a - c) + abs(b - d) == 1
                    for a, b in groups[first]
                    for c, d in groups[second]
                )
                if touching:
                    groups[first] |= groups.pop(second)
                    merged = True
                    break
            if merged:
                break
    return max((len(group) for group in groups), default=0)


def test_returns_the_area_of_the_largest_island() -> None:
    """Returns the size of the biggest island, not how many there are."""
    grid = [
        [1, 1, 0, 0],
        [1, 0, 0, 0],
        [0, 0, 1, 0],
    ]

    assert largest_island(grid) == 3


def test_picks_the_larger_of_two_islands() -> None:
    """Returns the larger area whichever island is met first."""
    assert largest_island([[1, 0, 1, 1, 1]]) == 3
    assert largest_island([[1, 1, 1, 0, 1]]) == 3


def test_does_not_join_islands_across_a_diagonal() -> None:
    """Treats diagonally touching cells as separate islands."""
    assert largest_island([[1, 0], [0, 1]]) == 1


def test_returns_zero_when_there_is_no_land() -> None:
    """Returns 0 for a grid of water, an empty grid and empty rows."""
    assert largest_island([[0, 0], [0, 0]]) == 0
    assert largest_island([]) == 0
    assert largest_island([[], []]) == 0


def test_counts_each_cell_of_a_block_once() -> None:
    """Counts a solid block's cells once each.

    In a 3x3 block almost every cell has two neighbours already on the stack
    when it is reached. A flood that marks a cell on the way out rather than
    on the way in pushes those cells twice and reports more than nine.
    """
    assert largest_island([[1, 1, 1], [1, 1, 1], [1, 1, 1]]) == 9


def test_follows_an_island_round_corners() -> None:
    """Follows a single island that bends."""
    grid = [
        [1, 1, 1],
        [0, 0, 1],
        [1, 1, 1],
    ]

    assert largest_island(grid) == 7


def test_agrees_with_merging_for_every_small_grid() -> None:
    """Matches a merge-the-neighbours count for every 3x3 and 2x4 grid."""
    for rows, columns in ((3, 3), (2, 4)):
        for cells in product((0, 1), repeat=rows * columns):
            grid = [
                list(cells[row * columns : (row + 1) * columns]) for row in range(rows)
            ]
            expected = by_merging(grid)
            assert largest_island([list(row) for row in grid]) == expected, grid


def test_returns_an_int() -> None:
    """Returns an int rather than a bool."""
    assert type(largest_island([[1]])) is int


def test_measures_one_island_of_ninety_thousand_cells() -> None:
    """Measures an island far larger than Python will recurse over."""
    side = 300

    assert largest_island([[1] * side for _ in range(side)]) == side * side
