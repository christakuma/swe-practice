"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import spiral_order


def reference(matrix: list[list[int]]) -> list[int]:
    """Spiral by peeling the top row and rotating the rest.

    An independent oracle.

    Elegant, allocates a new grid on every turn, and shares no boundary
    arithmetic with a four-pointer implementation. The two agree only if both
    are right.
    """
    remaining = [list(row) for row in matrix]
    values: list[int] = []
    while remaining:
        values.extend(remaining.pop(0))
        remaining = [list(row) for row in zip(*remaining, strict=False)][::-1]
    return values


def grid(rows: int, columns: int) -> list[list[int]]:
    """Return a rows x columns grid of distinct values."""
    return [
        [row * columns + column for column in range(columns)] for row in range(rows)
    ]


def test_spirals_a_three_by_three() -> None:
    """Reads a 3x3 matrix in spiral order."""
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

    assert spiral_order(matrix) == [1, 2, 3, 6, 9, 8, 7, 4, 5]


def test_handles_an_empty_matrix() -> None:
    """Returns nothing for an empty matrix."""
    assert spiral_order([]) == []


def test_handles_a_matrix_of_empty_rows() -> None:
    """Returns nothing for a matrix with rows but no columns."""
    assert spiral_order([[], [], []]) == []


def test_handles_a_single_cell() -> None:
    """Returns the one value in a 1x1 matrix."""
    assert spiral_order([[7]]) == [7]


def test_handles_a_single_row() -> None:
    """Reads a single row left to right, once.

    With one row, `top` and `bottom` are the same, so an unguarded bottom pass
    reads it straight back again and the output is twice as long as the input.
    """
    assert spiral_order([[1, 2, 3, 4]]) == [1, 2, 3, 4]


def test_handles_a_single_column() -> None:
    """Reads a single column top to bottom, once.

    The mirror of the single-row case, caught by the guard on the left pass.
    """
    assert spiral_order([[1], [2], [3], [4]]) == [1, 2, 3, 4]


def test_handles_a_wide_matrix() -> None:
    """Reads a matrix wider than it is tall."""
    assert spiral_order([[1, 2, 3, 4], [5, 6, 7, 8]]) == [1, 2, 3, 4, 8, 7, 6, 5]


def test_handles_a_tall_matrix() -> None:
    """Reads a matrix taller than it is wide."""
    matrix = [[1, 2], [3, 4], [5, 6]]

    assert spiral_order(matrix) == [1, 2, 4, 6, 5, 3]


def test_ends_on_a_single_middle_row() -> None:
    """Handles an inner ring that has collapsed to one row.

    3x5 leaves a 1x3 strip in the middle after the outer ring. This is the
    shape where a missing guard duplicates the innermost values rather than the
    outermost ones, so the output length is wrong but its start and end are not.
    """
    matrix = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14, 15]]

    assert spiral_order(matrix) == [
        1,
        2,
        3,
        4,
        5,
        10,
        15,
        14,
        13,
        12,
        11,
        6,
        7,
        8,
        9,
    ]


def test_ends_on_a_single_middle_column() -> None:
    """Handles an inner ring that has collapsed to one column."""
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14, 15]]

    assert spiral_order(matrix) == [
        1,
        2,
        3,
        6,
        9,
        12,
        15,
        14,
        13,
        10,
        7,
        4,
        5,
        8,
        11,
    ]


def test_returns_every_value_exactly_once() -> None:
    """Returns each value once -- no duplicates and nothing dropped."""
    for rows in range(1, 9):
        for columns in range(1, 9):
            matrix = grid(rows, columns)
            flat = sorted(value for row in matrix for value in row)

            assert sorted(spiral_order(matrix)) == flat, (rows, columns)


def test_agrees_with_an_independent_spiral_at_every_small_shape() -> None:
    """Matches a peel-and-rotate spiral for every shape up to 8x8.

    Eighty-one shapes, including every degenerate one. The guard bug survives
    all square cases, so a sweep that varies both dimensions is what finds it.
    """
    for rows in range(9):
        for columns in range(9):
            matrix = grid(rows, columns)

            assert spiral_order(matrix) == reference(matrix), (rows, columns)


def test_leaves_the_input_alone() -> None:
    """Does not consume or mutate the matrix it was given.

    Peeling rows off the caller's list is a correct way to spiral and destroys
    their data.
    """
    matrix = grid(3, 4)
    original = [list(row) for row in matrix]

    spiral_order(matrix)

    assert matrix == original


def test_handles_a_large_matrix() -> None:
    """Spirals a 400x400 matrix within the time limit."""
    n = 400
    matrix = grid(n, n)

    values = spiral_order(matrix)

    assert len(values) == n * n
    assert values[0] == 0
    assert values[n - 1] == n - 1
