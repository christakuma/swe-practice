"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import shortest_path

type Grid = list[list[int]]


def without_breaking(grid: Grid) -> int:
    """The standard shortest path: -1 if either end is a wall or nothing connects."""
    rows, columns = len(grid), len(grid[0])
    if grid[0][0] or grid[-1][-1]:
        return -1
    distance = {(0, 0): 1}
    queue = [(0, 0)]
    for row, column in queue:
        for cell in (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        ):
            inside = 0 <= cell[0] < rows and 0 <= cell[1] < columns
            if inside and not grid[cell[0]][cell[1]] and cell not in distance:
                distance[cell] = distance[row, column] + 1
                queue.append(cell)
    return distance.get((rows - 1, columns - 1), -1)


def by_removing_each_wall(grid: Grid) -> int:
    """The best standard path over the grid as it is and with each wall removed."""
    found = [without_breaking(grid)]
    for row, column in product(range(len(grid)), range(len(grid[0]))):
        if grid[row][column]:
            opened = [list(line) for line in grid]
            opened[row][column] = 0
            found.append(without_breaking(opened))
    reachable = [cells for cells in found if cells > 0]
    return min(reachable) if reachable else -1


def test_breaks_through_a_solid_wall() -> None:
    """Finds a route through a wall that cannot be walked round."""
    grid = [
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
    ]

    assert shortest_path(grid) == 5


def test_takes_a_shortcut_through_a_wall() -> None:
    """Uses the break to shorten a route that exists without it.

    The open route doubles back across the middle row and is eleven cells
    long. Going straight down the right-hand side through one wall is seven,
    which is as short as any route across a 5 x 3 grid can be.
    """
    grid = [
        [0, 0, 0],
        [1, 1, 0],
        [0, 0, 0],
        [0, 1, 1],
        [0, 0, 0],
    ]

    assert without_breaking(grid) == 11
    assert shortest_path(grid) == 7


def test_does_not_break_a_wall_it_does_not_need() -> None:
    """Returns the plain shortest route when no break could shorten it."""
    grid = [
        [0, 0, 0],
        [1, 1, 0],
        [0, 0, 0],
    ]

    assert shortest_path(grid) == 5
    assert shortest_path([[0, 0], [0, 0]]) == 3


def test_cannot_pass_two_walls() -> None:
    """Returns -1 when every route would need a second break."""
    assert shortest_path([[0, 1, 1, 0]]) == -1
    assert shortest_path([[0, 1], [1, 1], [1, 0]]) == -1


def test_saves_the_break_for_the_wall_that_needs_it() -> None:
    """Passes up walls near the start because a later wall cannot be avoided.

    The destination is sealed in behind walls, so the route has to arrive
    beside it with its break unspent. Two walls near the start offer ways
    into the middle of the grid that are exactly as short as the open way. A
    search that remembers only the first arrival at each cell records the
    middle as reached through one of them, whichever order it tries its
    moves in, and then cannot finish.
    """
    grid = [
        [0, 0, 1, 0],
        [1, 0, 0, 1],
        [0, 1, 1, 0],
    ]

    assert shortest_path(grid) == 6


def test_a_wall_at_either_end_uses_the_break() -> None:
    """Allows a wall as the start or the destination, and not as both."""
    assert shortest_path([[1, 0, 0]]) == 3
    assert shortest_path([[0, 0, 1]]) == 3
    assert shortest_path([[1, 0, 1]]) == -1
    assert shortest_path([[1, 1]]) == -1
    assert shortest_path([[1, 0], [1, 0]]) == 3


def test_a_single_cell() -> None:
    """Returns 1 for a 1 x 1 grid, open or wall."""
    assert shortest_path([[0]]) == 1
    assert shortest_path([[1]]) == 1


def test_an_empty_grid_has_no_route() -> None:
    """Returns -1 for a grid with no rows or no columns."""
    assert shortest_path([]) == -1
    assert shortest_path([[]]) == -1


def test_agrees_with_removing_each_wall_in_turn() -> None:
    """Matches a try-every-wall search for every small grid.

    Every 3 x 3 grid, every 2 x 5 grid and every 4 x 3 grid.
    """
    for rows, columns in ((3, 3), (2, 5), (4, 3)):
        for cells in product((0, 1), repeat=rows * columns):
            grid = [list(cells[r * columns : (r + 1) * columns]) for r in range(rows)]
            expected = by_removing_each_wall(grid)
            assert shortest_path([list(line) for line in grid]) == expected, grid


def test_crosses_a_large_grid() -> None:
    """Crosses a 199 x 200 grid of walls arranged as a comb.

    Every other row is solid except for a gap at alternating ends, which
    forces a route to sweep the full width of the grid on each open row.
    Breaking through one solid row saves one of those sweeps.
    """
    rows, columns = 199, 200
    grid = [[0] * columns for _ in range(rows)]
    for row in range(1, rows, 2):
        gap = columns - 1 if row % 4 == 1 else 0
        grid[row] = [1] * columns
        grid[row][gap] = 0

    plain = without_breaking(grid)

    assert plain > 50 * columns
    assert rows + columns - 1 <= shortest_path(grid) < plain
