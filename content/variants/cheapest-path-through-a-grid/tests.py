"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import cheapest_path


def by_walking_every_path(grid: list[list[int]], row: int = 0, column: int = 0) -> int:
    """The cheapest total from this cell on, trying both moves every time."""
    here = grid[row][column]
    onward = []
    if row + 1 < len(grid):
        onward.append(by_walking_every_path(grid, row + 1, column))
    if column + 1 < len(grid[0]):
        onward.append(by_walking_every_path(grid, row, column + 1))
    return here + (min(onward) if onward else 0)


def test_finds_the_cheapest_route() -> None:
    """Finds the least total across a small grid."""
    grid = [
        [1, 3, 1],
        [1, 5, 1],
        [4, 2, 1],
    ]

    assert cheapest_path(grid) == 7


def test_a_single_cell_costs_itself() -> None:
    """Returns the cell's own cost for a 1 x 1 grid, counted once."""
    assert cheapest_path([[5]]) == 5
    assert cheapest_path([[0]]) == 0


def test_a_single_row_or_column_has_one_path() -> None:
    """Adds up every cell when the grid is one row or one column."""
    assert cheapest_path([[1, 2, 3]]) == 6
    assert cheapest_path([[1], [2], [3]]) == 6


def test_includes_the_first_and_last_cells() -> None:
    """Counts the cost of the starting cell and of the finishing cell."""
    assert cheapest_path([[100, 0], [0, 0]]) == 100
    assert cheapest_path([[0, 0], [0, 100]]) == 100


def test_is_not_greedy() -> None:
    """Takes a dearer step first when the cheap one leads somewhere expensive."""
    grid = [
        [1, 2, 1],
        [1, 9, 1],
        [9, 9, 1],
    ]

    assert cheapest_path(grid) == 6


def test_the_edges_are_not_free() -> None:
    """Does not treat the space outside the grid as a route of cost zero."""
    grid = [
        [5, 9],
        [9, 5],
    ]

    assert cheapest_path(grid) == 19


def test_handles_grids_that_are_not_square() -> None:
    """Handles more rows than columns and more columns than rows."""
    wide = [[1, 1, 1, 1], [9, 9, 9, 1]]
    tall = [[1, 9], [1, 9], [1, 9], [1, 1]]

    assert cheapest_path(wide) == 5
    assert cheapest_path(tall) == 5


def test_agrees_with_walking_every_path() -> None:
    """Matches an exhaustive walk for every small grid.

    Every 3 x 3 grid and every 2 x 4 grid with costs drawn from 0, 1 and 5.
    """
    for rows, columns in ((3, 3), (2, 4), (4, 2)):
        for cells in product((0, 1, 5), repeat=rows * columns):
            grid = [
                list(cells[row * columns : (row + 1) * columns]) for row in range(rows)
            ]
            assert cheapest_path(grid) == by_walking_every_path(grid), grid


def test_leaves_the_grid_alone() -> None:
    """Does not modify the grid it was given."""
    grid = [[1, 2], [3, 4]]

    cheapest_path(grid)

    assert grid == [[1, 2], [3, 4]]


def test_crosses_a_large_grid() -> None:
    """Crosses a 300 x 300 grid, which has more paths than could ever be walked.

    Every cell costs 7 except a staircase of free cells along the diagonal
    and the cells just right of it, so the cheapest path costs nothing.
    """
    size = 300
    grid = [[7] * size for _ in range(size)]
    for index in range(size):
        grid[index][index] = 0
        if index + 1 < size:
            grid[index][index + 1] = 0

    assert cheapest_path(grid) == 0
    assert cheapest_path([[1] * size for _ in range(size)]) == 2 * size - 1
