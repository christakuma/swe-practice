"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import copy
import tracemalloc
from itertools import product

from solution import set_zeroes


def by_asking_every_pair(rows: list[list[int]]) -> list[list[int]]:
    """A cleared copy, by checking every cell against every original zero.

    An independent oracle. It names no diagonals: two cells are on a
    diagonal when they are as far apart down as they are across.
    """
    zeros = [
        (row, column)
        for row, cells in enumerate(rows)
        for column, value in enumerate(cells)
        if value == 0
    ]
    result = copy.deepcopy(rows)
    for row, cells in enumerate(rows):
        for column in range(len(cells)):
            for zero_row, zero_column in zeros:
                down, across = abs(row - zero_row), abs(column - zero_column)
                if min(down, across) == 0 or down == across:
                    result[row][column] = 0
                    break
    return result


def cleared(rows: list[list[int]]) -> list[list[int]]:
    matrix = copy.deepcopy(rows)
    result = set_zeroes(matrix)

    assert result is None, "set_zeroes should return nothing"
    return matrix


def test_a_zero_in_the_middle_reaches_every_cell_of_a_small_board() -> None:
    """Clears a whole 3 x 3 matrix from its centre."""
    assert cleared([[1, 2, 3], [4, 0, 6], [7, 8, 9]]) == [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]


def test_clears_the_row_and_the_column() -> None:
    """Clears along the row and up the column, as the original did.

    The zero is in the bottom-left corner, so one diagonal is on the board
    as well: up and to the right.
    """
    assert cleared([[1, 2, 3, 4, 5], [6, 7, 8, 9, 1], [0, 3, 4, 5, 6]]) == [
        [0, 2, 0, 4, 5],
        [0, 0, 8, 9, 1],
        [0, 0, 0, 0, 0],
    ]


def test_clears_the_diagonal_that_falls_to_the_right() -> None:
    """Clears down and to the right from a zero in the top-left corner."""
    assert cleared([[0, 2, 3, 4], [5, 6, 7, 8], [9, 1, 2, 3]]) == [
        [0, 0, 0, 0],
        [0, 0, 7, 8],
        [0, 1, 0, 3],
    ]


def test_clears_the_diagonal_that_falls_to_the_left() -> None:
    """Clears down and to the left from a zero in the top-right corner."""
    assert cleared([[1, 2, 3, 0], [5, 6, 7, 8], [9, 1, 2, 3]]) == [
        [0, 0, 0, 0],
        [5, 6, 0, 0],
        [9, 0, 2, 0],
    ]


def test_clears_diagonals_upward_as_well_as_downward() -> None:
    """Clears in all four diagonal directions from a zero on the bottom row."""
    assert cleared([[1, 2, 3, 4, 5], [6, 7, 8, 9, 1], [2, 3, 0, 5, 6]]) == [
        [0, 2, 0, 4, 0],
        [6, 0, 0, 0, 1],
        [0, 0, 0, 0, 0],
    ]


def test_does_not_cascade_from_the_zeros_it_writes() -> None:
    """Clears only from the zeros that were there to begin with.

    One zero in a corner of a 4 x 4 matrix leaves six cells standing. If
    the zeros written along its lines were allowed to clear lines of their
    own, nothing would be left.
    """
    assert cleared([[0, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]) == [
        [0, 0, 0, 0],
        [0, 0, 1, 1],
        [0, 1, 0, 1],
        [0, 1, 1, 0],
    ]


def test_handles_a_matrix_with_no_zeros() -> None:
    """Leaves a matrix without zeros untouched."""
    assert cleared([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]


def test_handles_empty_matrices() -> None:
    """Accepts a matrix with no rows and a matrix whose rows are empty."""
    assert cleared([]) == []
    assert cleared([[], []]) == [[], []]


def test_handles_a_single_row_and_a_single_column() -> None:
    """Clears the whole of a one-line matrix that holds a zero."""
    assert cleared([[1, 0, 3]]) == [[0, 0, 0]]
    assert cleared([[1], [0], [3]]) == [[0], [0], [0]]
    assert cleared([[1, 2, 3]]) == [[1, 2, 3]]


def test_tells_diagonals_apart_on_a_wide_matrix() -> None:
    """Does not confuse a diagonal above the main one with one below it.

    The zero is on the diagonal one step above the main diagonal. In a
    list indexed by row minus column that is index -1, which Python reads
    as the last entry -- the entry for some other diagonal entirely.
    """
    assert cleared([[1, 0, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]) == [
        [0, 0, 0, 0],
        [0, 0, 0, 1],
        [1, 0, 1, 0],
        [1, 0, 1, 1],
    ]
    assert cleared([[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [0, 1, 1, 1]]) == [
        [0, 1, 1, 0],
        [0, 1, 0, 1],
        [0, 0, 1, 1],
        [0, 0, 0, 0],
    ]


def test_handles_non_square_matrices_both_ways_round() -> None:
    """Clears diagonals that run off the short side of a tall or a wide matrix."""
    tall = [[1, 1], [1, 1], [1, 0], [1, 1], [1, 1]]
    wide = [[1, 1, 1, 1, 1], [1, 1, 0, 1, 1]]

    assert cleared(tall) == [[1, 0], [0, 0], [0, 0], [0, 0], [1, 0]]
    assert cleared(wide) == [[1, 0, 0, 0, 1], [0, 0, 0, 0, 0]]


def test_mutates_the_grid_the_caller_holds() -> None:
    """Changes the caller's rows where they are, without replacing them."""
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 0]]
    rows = list(matrix)

    set_zeroes(matrix)

    assert all(now is before for now, before in zip(matrix, rows, strict=True))
    assert matrix == [[0, 2, 0], [4, 0, 0], [0, 0, 0]]


def test_agrees_with_asking_every_pair_on_every_small_matrix() -> None:
    """Matches a cell-against-every-zero check for every 0/1 matrix of several shapes.

    Tall, wide and square, up to twelve cells: every possible arrangement of
    zeros in each.
    """
    for rows, columns in (
        (1, 1),
        (1, 4),
        (4, 1),
        (2, 2),
        (2, 3),
        (3, 2),
        (3, 3),
        (3, 4),
        (4, 3),
        (2, 5),
    ):
        for cells in product((0, 1), repeat=rows * columns):
            matrix = [
                list(cells[row * columns : (row + 1) * columns]) for row in range(rows)
            ]

            assert cleared(matrix) == by_asking_every_pair(matrix), matrix


def test_handles_a_large_matrix() -> None:
    """Clears a 200 x 150 matrix from three zeros.

    The expected matrix is built from the definition of a queen's move,
    one zero at a time.
    """
    rows, columns = 200, 150
    matrix = [
        [row * columns + column + 1 for column in range(columns)] for row in range(rows)
    ]
    zeros = [(0, 149), (120, 30), (199, 75)]
    for row, column in zeros:
        matrix[row][column] = 0
    expected = copy.deepcopy(matrix)
    for row in range(rows):
        for column in range(columns):
            for zero_row, zero_column in zeros:
                down, across = abs(row - zero_row), abs(column - zero_column)
                if min(down, across) == 0 or down == across:
                    expected[row][column] = 0

    set_zeroes(matrix)

    assert matrix == expected
    assert sum(value != 0 for cells in matrix for value in cells) > 20_000


def test_remembers_lines_and_not_cells() -> None:
    """Clears a 200 x 200 matrix with ten thousand zeros in little extra memory.

    A copy of the matrix is forty thousand references. So is a list of
    where the zeros are, when a quarter of the cells are zeros. Flags for
    the lines are a few hundred entries however many zeros there are.
    """
    size = 200
    matrix = [
        [0 if row % 2 == 0 and column % 2 == 0 else 7 for column in range(size)]
        for row in range(size)
    ]

    tracemalloc.start()
    set_zeroes(matrix)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 64_000, f"allocated {peak} bytes"
    assert all(value == 0 for cells in matrix for value in cells)
