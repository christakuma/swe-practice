"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import shortest_path


def by_relaxing(grid: list[list[int]]) -> int:
    """Lower every cell's distance from its neighbours until nothing changes."""
    if not grid or grid[0][0] == 1 or grid[-1][-1] == 1:
        return -1
    rows, columns = len(grid), len(grid[0])
    far = rows * columns + 1
    best = [[far] * columns for _ in range(rows)]
    best[0][0] = 1
    changed = True
    while changed:
        changed = False
        for y, x in product(range(rows), range(columns)):
            if grid[y][x] == 1:
                continue
            for a, b in product(
                range(max(y - 1, 0), min(y + 2, rows)),
                range(max(x - 1, 0), min(x + 2, columns)),
            ):
                if best[a][b] + 1 < best[y][x]:
                    best[y][x] = best[a][b] + 1
                    changed = True
    return -1 if best[-1][-1] >= far else best[-1][-1]


def test_cuts_the_corner() -> None:
    """Crosses an open 3x3 grid in three cells."""
    assert shortest_path([[0, 0, 0], [0, 0, 0], [0, 0, 0]]) == 3


def test_slips_between_two_walls() -> None:
    """Steps diagonally between walls that touch at a corner."""
    assert shortest_path([[0, 1], [1, 0]]) == 2


def test_returns_minus_one_when_blocked() -> None:
    """Returns -1 when there is no route, or an end is a wall."""
    assert shortest_path([[0, 1, 1], [1, 1, 0]]) == -1
    assert shortest_path([[1, 0], [0, 0]]) == -1
    assert shortest_path([[0, 0], [0, 1]]) == -1
    assert shortest_path([]) == -1


def test_counts_the_start_as_a_cell() -> None:
    """Returns 1 when the start is the destination."""
    assert shortest_path([[0]]) == 1


def test_takes_the_longer_dimension_on_an_open_grid() -> None:
    """Needs as many cells as the longer side of an open rectangle."""
    assert shortest_path([[0] * 5 for _ in range(2)]) == 5


def test_agrees_with_relaxing_every_small_grid() -> None:
    """Matches a relax-until-stable search for every 3x3 and 2x4 grid."""
    for rows, columns in ((3, 3), (2, 4)):
        for cells in product((0, 1), repeat=rows * columns):
            grid = [list(cells[y * columns : (y + 1) * columns]) for y in range(rows)]
            expected = by_relaxing(grid)
            assert shortest_path([list(line) for line in grid]) == expected, grid


def test_crosses_a_large_open_grid() -> None:
    """Crosses a 200x200 open grid within the time limit."""
    assert shortest_path([[0] * 200 for _ in range(200)]) == 200
