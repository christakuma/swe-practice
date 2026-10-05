"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import set_zeroes


def reference(matrix: list[list[int]]) -> list[list[int]]:
    """Clear rows and columns by building a new grid, from sets of indices.

    An independent oracle. It is allowed the O(m + n) space the real solution
    is not, and it shares no marker bookkeeping with it.
    """
    if not matrix or not matrix[0]:
        return [list(row) for row in matrix]
    rows, columns = len(matrix), len(matrix[0])
    zero_rows = {
        r for r in range(rows) if any(matrix[r][c] == 0 for c in range(columns))
    }
    zero_columns = {
        c for c in range(columns) if any(matrix[r][c] == 0 for r in range(rows))
    }
    return [
        [
            0 if r in zero_rows or c in zero_columns else matrix[r][c]
            for c in range(columns)
        ]
        for r in range(rows)
    ]


def test_clears_a_cross_through_one_zero() -> None:
    """Zeroes the row and column of a single interior zero."""
    matrix = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]

    set_zeroes(matrix)

    assert matrix == [[1, 0, 1], [0, 0, 0], [1, 0, 1]]


def test_does_not_cascade_from_the_zeros_it_writes() -> None:
    """Clears from the original zeros only.

    A solution that clears as it scans cannot tell its own zeros from the
    input's, so the clearing spreads until the entire matrix is zero. Here the
    correct answer still holds four ones.
    """
    matrix = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]

    set_zeroes(matrix)

    assert sum(value for row in matrix for value in row) == 4


def test_handles_a_matrix_with_no_zeros() -> None:
    """Leaves a matrix without zeros untouched."""
    matrix = [[1, 2], [3, 4]]

    set_zeroes(matrix)

    assert matrix == [[1, 2], [3, 4]]


def test_handles_an_all_zero_matrix() -> None:
    """Leaves an all-zero matrix all zero."""
    matrix = [[0, 0], [0, 0]]

    set_zeroes(matrix)

    assert matrix == [[0, 0], [0, 0]]


def test_handles_an_empty_matrix() -> None:
    """Returns without raising on an empty matrix."""
    matrix: list[list[int]] = []

    set_zeroes(matrix)

    assert matrix == []


def test_handles_a_zero_in_the_first_row() -> None:
    """Clears correctly when the marker strip itself holds an original zero.

    Row zero and column zero are where a marker-based solution stores its
    notes, so an original zero sitting in them is the case that confuses it.
    """
    matrix = [[1, 0, 1], [1, 1, 1]]

    set_zeroes(matrix)

    assert matrix == [[0, 0, 0], [1, 0, 1]]


def test_handles_a_zero_in_the_first_column() -> None:
    """Clears correctly for an original zero in column zero."""
    matrix = [[1, 1], [0, 1]]

    set_zeroes(matrix)

    assert matrix == [[0, 1], [0, 0]]


def test_handles_a_zero_at_the_origin() -> None:
    """Clears row zero and column zero when the zero is at (0, 0).

    (0, 0) is the cell a naive marker scheme asks to mean two things at once.
    """
    matrix = [[0, 1, 1], [1, 1, 1], [1, 1, 1]]

    set_zeroes(matrix)

    assert matrix == [[0, 0, 0], [0, 1, 1], [0, 1, 1]]


def test_handles_a_single_row() -> None:
    """Clears a single row entirely when it holds a zero."""
    matrix = [[1, 0, 1]]

    set_zeroes(matrix)

    assert matrix == [[0, 0, 0]]


def test_handles_a_single_column() -> None:
    """Clears a single column entirely when it holds a zero."""
    matrix = [[1], [0], [1]]

    set_zeroes(matrix)

    assert matrix == [[0], [0], [0]]


def test_mutates_the_grid_the_caller_holds() -> None:
    """Clears in place rather than rebuilding.

    Nothing is returned, so rebinding a local or replacing the row lists leaves
    the caller holding unmodified data.
    """
    matrix = [[1, 0], [1, 1]]
    rows = [matrix[0], matrix[1]]

    set_zeroes(matrix)

    assert matrix[0] is rows[0]
    assert matrix[1] is rows[1]


def test_agrees_with_a_reference_on_every_small_zero_one_matrix() -> None:
    """Matches the reference for every 0/1 matrix up to 3x4.

    Four thousand shapes at the largest size, which is every possible
    arrangement of zeros. Marker schemes fail on specific configurations --
    a zero in row zero but not column zero, or the reverse -- and enumerating
    them all is cheaper than reasoning about which ones matter.
    """
    for rows in range(1, 4):
        for columns in range(1, 5):
            for bits in product((0, 1), repeat=rows * columns):
                matrix = [
                    [bits[r * columns + c] for c in range(columns)] for r in range(rows)
                ]
                expected = reference(matrix)

                set_zeroes(matrix)

                assert matrix == expected, (rows, columns, bits)


def test_handles_a_large_matrix() -> None:
    """Clears a 200x200 matrix within the time limit."""
    size = 200
    matrix = [[1] * size for _ in range(size)]
    matrix[100][150] = 0

    set_zeroes(matrix)

    assert all(value == 0 for value in matrix[100])
    assert all(matrix[row][150] == 0 for row in range(size))
    assert matrix[0][0] == 1
    assert sum(value for row in matrix for value in row) == (size - 1) * (size - 1)
