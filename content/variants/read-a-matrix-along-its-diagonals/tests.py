"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import diagonal_order


def numbered(rows: int, columns: int) -> list[list[int]]:
    """A matrix holding 0, 1, 2, ... in reading order."""
    return [
        [row * columns + column for column in range(columns)] for row in range(rows)
    ]


def by_walking(matrix: list[list[int]]) -> list[int]:
    """Step one cell at a time, turning at the edges."""
    rows, columns = len(matrix), len(matrix[0])
    row = column = 0
    rising = True
    seen = []
    for _ in range(rows * columns):
        seen.append(matrix[row][column])
        if rising:
            if column == columns - 1:
                row, rising = row + 1, False
            elif row == 0:
                column, rising = column + 1, False
            else:
                row, column = row - 1, column + 1
        elif row == rows - 1:
            column, rising = column + 1, True
        elif column == 0:
            row, rising = row + 1, True
        else:
            row, column = row + 1, column - 1
    return seen


def test_reads_a_square_matrix() -> None:
    """Zigzags across a 3 x 3 matrix."""
    matrix = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]

    assert diagonal_order(matrix) == [1, 2, 4, 7, 5, 3, 6, 8, 9]


def test_the_second_diagonal_runs_down_and_left() -> None:
    """Goes right before down after the first cell."""
    assert diagonal_order([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_the_direction_alternates() -> None:
    """Reverses direction on every diagonal, not just the first few."""
    assert diagonal_order(numbered(4, 4)) == [
        0,
        1,
        4,
        8,
        5,
        2,
        3,
        6,
        9,
        12,
        13,
        10,
        7,
        11,
        14,
        15,
    ]


def test_reads_a_wide_matrix() -> None:
    """Handles more columns than rows."""
    matrix = [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
    ]

    assert diagonal_order(matrix) == [1, 2, 5, 6, 3, 4, 7, 8]


def test_reads_a_tall_matrix() -> None:
    """Handles more rows than columns."""
    matrix = [
        [1, 2],
        [3, 4],
        [5, 6],
        [7, 8],
    ]

    assert diagonal_order(matrix) == [1, 2, 3, 5, 4, 6, 7, 8]


def test_a_single_row_or_column_reads_straight_through() -> None:
    """Returns one row or one column in its own order."""
    assert diagonal_order([[1, 2, 3]]) == [1, 2, 3]
    assert diagonal_order([[1], [2], [3]]) == [1, 2, 3]
    assert diagonal_order([[7]]) == [7]


def test_an_empty_matrix_has_nothing_to_read() -> None:
    """Returns [] for a matrix with no rows or no columns."""
    assert diagonal_order([]) == []
    assert diagonal_order([[]]) == []


def test_visits_every_cell_once() -> None:
    """Returns each element exactly once, repeated values included."""
    matrix = [[5, 5, 5], [5, 5, 5]]

    assert diagonal_order(matrix) == [5] * 6
    assert sorted(diagonal_order(numbered(5, 7))) == list(range(35))


def test_agrees_with_walking_cell_by_cell() -> None:
    """Matches a step-by-step walk for every shape up to 7 x 7."""
    for rows in range(1, 8):
        for columns in range(1, 8):
            matrix = numbered(rows, columns)
            assert diagonal_order(matrix) == by_walking(matrix), (rows, columns)


def test_leaves_the_matrix_alone() -> None:
    """Does not modify the matrix."""
    matrix = [[1, 2], [3, 4]]

    diagonal_order(matrix)

    assert matrix == [[1, 2], [3, 4]]


def test_reads_a_large_matrix() -> None:
    """Reads a 300 x 250 matrix."""
    matrix = numbered(300, 250)

    order = diagonal_order(matrix)

    assert len(order) == 75_000
    assert order[:6] == [0, 1, 250, 500, 251, 2]
    assert order[-3:] == [74_749, 74_998, 74_999]
    assert order == by_walking(matrix)
