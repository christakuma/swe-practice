"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product
from math import comb

from solution import count_paths


def by_walking(grid: list[list[int]], y: int = 0, x: int = 0) -> int:
    """Walk every path."""
    if y >= len(grid) or x >= len(grid[0]) or grid[y][x] == 1:
        return 0
    if (y, x) == (len(grid) - 1, len(grid[0]) - 1):
        return 1
    return by_walking(grid, y + 1, x) + by_walking(grid, y, x + 1)


def test_goes_round_an_obstacle() -> None:
    """Counts the two paths round a blocked centre."""
    assert count_paths([[0, 0, 0], [0, 1, 0], [0, 0, 0]]) == 2


def test_matches_the_open_grid_when_nothing_is_blocked() -> None:
    """Gives the open-grid counts when there are no obstacles."""
    assert count_paths([[0] * 3 for _ in range(2)]) == 3
    assert count_paths([[0] * 7 for _ in range(3)]) == 28


def test_a_blocked_end_leaves_no_paths() -> None:
    """Returns 0 when the start or the destination is blocked."""
    assert count_paths([[1, 0], [0, 0]]) == 0
    assert count_paths([[0, 0], [0, 1]]) == 0
    assert count_paths([[1]]) == 0


def test_an_obstacle_cuts_off_the_edge_beyond_it() -> None:
    """Does not treat the first row or column as always reachable."""
    assert count_paths([[0, 1, 0, 0]]) == 0
    assert count_paths([[0, 1, 0], [0, 0, 0]]) == 1


def test_handles_empty_and_tiny_grids() -> None:
    """Returns 0 for no grid and 1 for a single open cell."""
    assert count_paths([]) == 0
    assert count_paths([[]]) == 0
    assert count_paths([[0]]) == 1


def test_agrees_with_walking_every_path() -> None:
    """Matches a walk of every path, for every grid up to 3x4."""
    for rows, columns in ((1, 4), (2, 3), (3, 3), (3, 4)):
        for cells in product((0, 1), repeat=rows * columns):
            grid = [list(cells[y * columns : (y + 1) * columns]) for y in range(rows)]
            assert count_paths(grid) == by_walking(grid), grid


def test_counts_a_large_grid_exactly() -> None:
    """Returns an exact count for a 300x300 grid."""
    side = 300
    open_grid = [[0] * side for _ in range(side)]

    assert count_paths(open_grid) == comb(2 * side - 2, side - 1)

    open_grid[150] = [1] * side

    assert count_paths(open_grid) == 0
