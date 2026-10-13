"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import spiral_matrix


def read_in_spiral(matrix: list[list[int]]) -> list[int]:
    """Read a matrix in spiral order by peeling the top row and turning."""
    remaining = [list(row) for row in matrix]
    values: list[int] = []
    while remaining:
        values += remaining.pop(0)
        remaining = [list(row) for row in zip(*remaining, strict=True)][::-1]
    return values


def test_builds_a_three_by_three() -> None:
    """Builds the 3x3 spiral."""
    assert spiral_matrix(3) == [[1, 2, 3], [8, 9, 4], [7, 6, 5]]


def test_builds_a_four_by_four() -> None:
    """Builds the 4x4 spiral, whose inner ring is a 2x2."""
    assert spiral_matrix(4) == [
        [1, 2, 3, 4],
        [12, 13, 14, 5],
        [11, 16, 15, 6],
        [10, 9, 8, 7],
    ]


def test_builds_the_smallest_squares() -> None:
    """Builds the 0x0, 1x1 and 2x2 spirals."""
    assert spiral_matrix(0) == []
    assert spiral_matrix(1) == [[1]]
    assert spiral_matrix(2) == [[1, 2], [4, 3]]


def test_reads_back_as_one_to_n_squared_at_every_small_size() -> None:
    """Reads back in spiral order as 1, 2, 3, ... for every size up to 25."""
    for size in range(26):
        matrix = spiral_matrix(size)
        assert len(matrix) == size
        assert all(len(row) == size for row in matrix)
        assert read_in_spiral(matrix) == list(range(1, size * size + 1)), size


def test_gives_every_row_its_own_list() -> None:
    """Returns rows that are separate lists, not one list repeated."""
    matrix = spiral_matrix(4)

    assert len({id(row) for row in matrix}) == 4


def test_builds_a_large_spiral() -> None:
    """Builds a 400x400 spiral within the time limit."""
    matrix = spiral_matrix(400)

    assert matrix[0][:3] == [1, 2, 3]
    assert matrix[1][0] == 4 * 399
    assert read_in_spiral(matrix) == list(range(1, 160_001))
