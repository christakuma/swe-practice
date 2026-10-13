"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import set_zeroes


def cleared(matrix: list[list[int]]) -> list[list[int]]:
    """What the matrix should become, built as a new one."""
    rows = {y for y, line in enumerate(matrix) if 0 in line}
    columns = {x for line in matrix for x, value in enumerate(line) if value == 0}
    return [
        [0 if y in rows or x in columns else value for x, value in enumerate(line)]
        for y, line in enumerate(matrix)
    ]


def differences(before: list[list[int]], after: list[list[int]]) -> int:
    return sum(
        a != b
        for old, new in zip(before, after, strict=True)
        for a, b in zip(old, new, strict=True)
    )


def test_counts_the_cells_that_changed() -> None:
    """Returns 4 for a single zero in the middle of a 3x3."""
    matrix = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]

    assert set_zeroes(matrix) == 4
    assert matrix == [[1, 0, 1], [0, 0, 0], [1, 0, 1]]


def test_does_not_count_a_crossing_twice() -> None:
    """Counts a cell in a cleared row and a cleared column once."""
    matrix = [[0, 1], [1, 0]]

    assert set_zeroes(matrix) == 2
    assert matrix == [[0, 0], [0, 0]]


def test_does_not_count_cells_that_were_already_zero() -> None:
    """Returns 0 when everything to be cleared is zero already."""
    matrix = [[0, 0], [0, 0]]

    assert set_zeroes(matrix) == 0


def test_returns_zero_when_nothing_changes() -> None:
    """Returns 0 for a matrix with no zeros, and for an empty one."""
    matrix = [[1, 2], [3, 4]]

    assert set_zeroes(matrix) == 0
    assert matrix == [[1, 2], [3, 4]]
    assert set_zeroes([]) == 0


def test_only_original_zeros_trigger_clearing() -> None:
    """Does not let a zero it wrote clear another row or column."""
    matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]

    assert set_zeroes(matrix) == 4
    assert matrix == [[0, 0, 0], [0, 4, 5], [0, 7, 8]]


def test_agrees_with_a_rebuilt_matrix_for_every_small_case() -> None:
    """Matches a rebuilt matrix and a cell-by-cell count for every small case."""
    for rows, columns in ((1, 3), (2, 2), (2, 3), (3, 3)):
        for cells in product((0, 1, 2), repeat=rows * columns):
            if rows * columns == 9 and 2 in cells:
                continue
            before = [list(cells[y * columns : (y + 1) * columns]) for y in range(rows)]
            matrix = [list(line) for line in before]
            expected = cleared(before)
            assert set_zeroes(matrix) == differences(before, expected), before
            assert matrix == expected, before


def test_clears_a_large_matrix() -> None:
    """Clears a 200x200 matrix within the time limit."""
    side = 200
    matrix = [[1] * side for _ in range(side)]
    matrix[10][20] = 0

    assert set_zeroes(matrix) == 2 * side - 2
