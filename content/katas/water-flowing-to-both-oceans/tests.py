"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import both_oceans

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def reference(heights: list[list[int]]) -> list[tuple[int, int]]:
    """Flood downhill from every cell and see which oceans it reaches.

    An independent oracle: it searches forwards, the direction the problem is
    posed in, so it shares no reasoning with the reverse-uphill solution.
    Quadratic, and fine at these sizes.
    """
    if not heights or not heights[0]:
        return []
    rows, columns = len(heights), len(heights[0])
    out: list[tuple[int, int]] = []
    for start_row in range(rows):
        for start_column in range(columns):
            seen = {(start_row, start_column)}
            stack = [(start_row, start_column)]
            top_left = bottom_right = False
            while stack:
                row, column = stack.pop()
                if row == 0 or column == 0:
                    top_left = True
                if row == rows - 1 or column == columns - 1:
                    bottom_right = True
                for row_step, column_step in STEPS:
                    next_row, next_column = row + row_step, column + column_step
                    if not (0 <= next_row < rows and 0 <= next_column < columns):
                        continue
                    if (next_row, next_column) in seen:
                        continue
                    if heights[next_row][next_column] > heights[row][column]:
                        continue
                    seen.add((next_row, next_column))
                    stack.append((next_row, next_column))
            if top_left and bottom_right:
                out.append((start_row, start_column))
    return sorted(out)


def test_handles_the_worked_example() -> None:
    """Returns the documented cells."""
    grid = [[1, 2, 2, 3], [3, 2, 3, 4], [2, 4, 5, 3]]

    assert both_oceans(grid) == [(0, 3), (1, 0), (1, 3), (2, 0), (2, 1), (2, 2)]


def test_handles_the_classic_five_by_five() -> None:
    """Returns the right cells for the well-known larger example."""
    grid = [
        [1, 2, 2, 3, 5],
        [3, 2, 3, 4, 4],
        [2, 4, 5, 3, 1],
        [6, 7, 1, 4, 5],
        [5, 1, 1, 2, 4],
    ]

    assert both_oceans(grid) == [
        (0, 4),
        (1, 3),
        (1, 4),
        (2, 2),
        (3, 0),
        (3, 1),
        (4, 0),
    ]


def test_handles_an_empty_grid() -> None:
    """Returns nothing for an empty grid."""
    assert both_oceans([]) == []
    assert both_oceans([[]]) == []


def test_handles_a_single_cell() -> None:
    """Returns the one cell, which touches both oceans at once."""
    assert both_oceans([[7]]) == [(0, 0)]


def test_handles_a_flat_grid() -> None:
    """Returns every cell when all heights are equal.

    Equal heights flow both ways, so a plateau is fully connected. Using a
    strict comparison in the uphill walk returns only the border here.
    """
    grid = [[3, 3, 3], [3, 3, 3], [3, 3, 3]]

    assert both_oceans(grid) == sorted(product(range(3), repeat=2))


def test_handles_a_single_row() -> None:
    """Returns every cell of a single row, which touches both oceans."""
    assert both_oceans([[1, 2, 3]]) == [(0, 0), (0, 1), (0, 2)]


def test_handles_a_single_column() -> None:
    """Returns every cell of a single column."""
    assert both_oceans([[1], [2], [3]]) == [(0, 0), (1, 0), (2, 0)]


def test_excludes_a_basin() -> None:
    """Leaves out a cell that is lower than everything around it."""
    grid = [[5, 5, 5], [5, 1, 5], [5, 5, 5]]
    result = both_oceans(grid)

    assert (1, 1) not in result
    assert (0, 0) in result


def test_includes_a_peak() -> None:
    """Includes a cell higher than everything around it."""
    grid = [[1, 1, 1], [1, 9, 1], [1, 1, 1]]
    result = both_oceans(grid)

    assert (1, 1) in result


def test_handles_a_ridge_that_only_reaches_one_ocean() -> None:
    """Leaves out cells that drain to only one ocean.

    A grid that rises steadily from the top-left: the low cells drain only to
    the near ocean and the high ones only to the far one, so only the cells on
    both borders qualify.
    """
    grid = [[1, 2, 3], [2, 3, 4], [3, 4, 5]]
    result = both_oceans(grid)

    assert result == reference(grid)
    assert (0, 0) not in result


def test_returns_sorted_pairs() -> None:
    """Returns the cells as sorted (row, column) tuples."""
    grid = [[1, 2], [3, 4]]

    result = both_oceans(grid)

    assert result == sorted(result)
    assert all(isinstance(cell, tuple) and len(cell) == 2 for cell in result)


def test_does_not_mutate_the_grid() -> None:
    """Leaves the heights as it found them.

    Marking visited cells by writing into the grid is a tempting way to avoid
    a set and destroys the caller's data.
    """
    grid = [[1, 2, 2, 3], [3, 2, 3, 4], [2, 4, 5, 3]]
    before = [list(row) for row in grid]

    both_oceans(grid)

    assert grid == before


def test_agrees_with_a_forward_search_on_every_small_grid() -> None:
    """Matches a downhill-from-every-cell oracle for every small grid.

    Every grid up to 3x3 over three height values -- around twenty thousand
    grids. The plateau handling and the two border seedings each fail only on
    particular height arrangements.
    """
    for rows in range(1, 4):
        for columns in range(1, 4):
            for values in product(range(3), repeat=rows * columns):
                grid = [
                    [values[row * columns + column] for column in range(columns)]
                    for row in range(rows)
                ]

                assert both_oceans(grid) == reference(grid), grid


def test_handles_a_large_flat_grid() -> None:
    """Handles a 200x200 flat grid within the time limit.

    The worst case for a forward search: every cell drains everywhere, so each
    of the forty thousand searches covers the whole grid. It is also the worst
    case for recursion depth, since the uphill walk can reach every cell.
    """
    size = 200
    grid = [[1] * size for _ in range(size)]

    assert len(both_oceans(grid)) == size * size
