"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import rotate


def square(size: int) -> list[list[int]]:
    """A size x size matrix holding 0, 1, 2, ... row by row."""
    return [list(range(row * size, (row + 1) * size)) for row in range(size)]


def turned(matrix: list[list[int]]) -> list[list[int]]:
    """The anticlockwise rotation, built as a new matrix."""
    return [list(row) for row in zip(*matrix, strict=True)][::-1]


def test_rotates_a_three_by_three() -> None:
    """Rotates a 3x3 matrix anticlockwise."""
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

    rotate(matrix)

    assert matrix == [[3, 6, 9], [2, 5, 8], [1, 4, 7]]


def test_rotates_anticlockwise_not_clockwise() -> None:
    """Sends the top-right corner to the top-left."""
    matrix = [[1, 2], [3, 4]]

    rotate(matrix)

    assert matrix == [[2, 4], [1, 3]]


def test_works_in_place_and_returns_nothing() -> None:
    """Mutates the matrix it was given and returns None."""
    matrix = [[1, 2], [3, 4]]
    same = matrix

    assert rotate(matrix) is None
    assert same == [[2, 4], [1, 3]]


def test_leaves_tiny_matrices_alone() -> None:
    """Leaves an empty and a 1x1 matrix as they are."""
    empty: list[list[int]] = []
    single = [[7]]

    rotate(empty)
    rotate(single)

    assert empty == []
    assert single == [[7]]


def test_agrees_with_a_rebuilt_rotation_at_every_small_size() -> None:
    """Matches a newly built rotation for every size from 0 to 12."""
    for size in range(13):
        matrix = square(size)
        rotate(matrix)
        assert matrix == turned(square(size)), size


def test_four_turns_restore_the_matrix() -> None:
    """Returns to the starting matrix after four quarter turns."""
    matrix = square(5)
    for _ in range(4):
        rotate(matrix)

    assert matrix == square(5)


def test_rotates_a_large_matrix() -> None:
    """Rotates a 300x300 matrix within the time limit."""
    matrix = square(300)

    rotate(matrix)

    assert matrix == turned(square(300))
