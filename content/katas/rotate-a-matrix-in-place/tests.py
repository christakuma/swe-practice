"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import rotate


def reference(matrix: list[list[int]]) -> list[list[int]]:
    """Rotate clockwise by building a new grid -- the banned one-liner.

    An independent oracle: it shares no index arithmetic with a transpose-and-
    reverse implementation, so the two agree only if both are right.
    """
    return [list(row) for row in zip(*matrix[::-1], strict=False)]


def grid(n: int) -> list[list[int]]:
    """Return an n x n grid of distinct values."""
    return [[row * n + column for column in range(n)] for row in range(n)]


def test_rotates_a_three_by_three() -> None:
    """Rotates a 3x3 matrix clockwise."""
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

    rotate(matrix)

    assert matrix == [[7, 4, 1], [8, 5, 2], [9, 6, 3]]


def test_rotates_a_two_by_two() -> None:
    """Rotates a 2x2 matrix clockwise."""
    matrix = [[1, 2], [3, 4]]

    rotate(matrix)

    assert matrix == [[3, 1], [4, 2]]


def test_handles_a_one_by_one() -> None:
    """Leaves a 1x1 matrix alone."""
    matrix = [[5]]

    rotate(matrix)

    assert matrix == [[5]]


def test_handles_an_empty_matrix() -> None:
    """Leaves an empty matrix alone without raising."""
    matrix: list[list[int]] = []

    rotate(matrix)

    assert matrix == []


def test_actually_changes_the_matrix() -> None:
    """Rotates rather than leaving the matrix untouched.

    Transposing with the inner loop over the full row range swaps every pair
    twice, so the matrix comes back exactly as it started. That failure looks
    like nothing happened, which is easy to misread as a harness problem.
    """
    matrix = grid(4)
    original = [list(row) for row in matrix]

    rotate(matrix)

    assert matrix != original


def test_mutates_the_grid_the_caller_holds() -> None:
    """Rotates in place rather than rebuilding.

    Nothing is returned, so a solution that assigns a freshly built grid to the
    local name does nothing at all from the caller's point of view. The row
    lists must be the same objects too, or only the outer list was reused.
    """
    matrix = grid(3)
    rows = [matrix[0], matrix[1], matrix[2]]

    rotate(matrix)

    assert matrix[0] is rows[0]
    assert matrix[1] is rows[1]
    assert matrix[2] is rows[2]


def test_agrees_with_an_independent_rotation_at_every_small_size() -> None:
    """Matches a newly built rotation for every size from 0 to 12.

    Off-by-one errors in the diagonal bound and transpose-then-reverse applied
    in the wrong order both survive the 2x2 and 3x3 cases often enough to be
    worth sweeping.
    """
    for n in range(13):
        matrix = grid(n)
        expected = reference(matrix)

        rotate(matrix)

        assert matrix == expected, n


def test_turns_clockwise_rather_than_anticlockwise() -> None:
    """Rotates clockwise, not anticlockwise.

    Reversing the rows before transposing instead of after gives the
    anticlockwise rotation. It is symmetric enough to pass a test that only
    checks the matrix changed, and it is wrong.
    """
    matrix = [[1, 2], [3, 4]]

    rotate(matrix)

    assert matrix[0][0] == 3


def test_preserves_every_value() -> None:
    """Keeps exactly the values it started with."""
    matrix = grid(6)
    expected = sorted(value for row in matrix for value in row)

    rotate(matrix)

    assert sorted(value for row in matrix for value in row) == expected


def test_four_rotations_return_the_original() -> None:
    """Returns to the starting matrix after four quarter turns.

    A property rather than a table: it holds for any square matrix and catches
    a rotation that is self-consistent but not actually a quarter turn.
    """
    matrix = grid(5)
    original = [list(row) for row in matrix]

    for _ in range(4):
        rotate(matrix)

    assert matrix == original


def test_rotates_a_large_matrix() -> None:
    """Rotates a 300x300 matrix within the time limit."""
    n = 300
    matrix = grid(n)

    rotate(matrix)

    assert matrix[0][0] == (n - 1) * n
    assert matrix[0][n - 1] == 0
    assert matrix[n - 1][n - 1] == n - 1
