"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import copy

from solution import rotate


def grid(n: int) -> list[list[int]]:
    """An `n x n` matrix whose values are all different."""
    return [[row * n + column for column in range(n)] for row in range(n)]


def stepped(rows: list[list[int]], turns: int) -> list[list[int]]:
    """A rotated copy, built one quarter turn at a time.

    An independent reference. It makes a fresh grid for every single turn
    and does no arithmetic on `turns` beyond counting down, so it is only
    usable for small counts -- which is the point.
    """
    result = [list(row) for row in rows]
    for _ in range(abs(turns)):
        if turns > 0:
            result = [list(row) for row in zip(*result[::-1], strict=True)]
        else:
            result = [list(row) for row in zip(*result, strict=True)][::-1]
    return result


def turned(rows: list[list[int]], turns: int) -> list[list[int]]:
    matrix = copy.deepcopy(rows)
    result = rotate(matrix, turns)

    assert result is None, "rotate should return nothing"
    return matrix


def test_one_turn_is_clockwise() -> None:
    """Moves the left column to the top row for a single turn."""
    assert turned([[1, 2, 3], [4, 5, 6], [7, 8, 9]], 1) == [
        [7, 4, 1],
        [8, 5, 2],
        [9, 6, 3],
    ]
    assert turned([[1, 2], [3, 4]], 1) == [[3, 1], [4, 2]]


def test_a_negative_turn_is_anticlockwise() -> None:
    """Moves the right column to the top row for a turn of -1."""
    assert turned([[1, 2, 3], [4, 5, 6], [7, 8, 9]], -1) == [
        [3, 6, 9],
        [2, 5, 8],
        [1, 4, 7],
    ]
    assert turned([[1, 2], [3, 4]], -1) == [[2, 4], [1, 3]]


def test_two_turns_is_a_half_turn() -> None:
    """Reads the matrix backwards for two turns in either direction."""
    assert turned([[1, 2, 3], [4, 5, 6], [7, 8, 9]], 2) == [
        [9, 8, 7],
        [6, 5, 4],
        [3, 2, 1],
    ]
    assert turned([[1, 2], [3, 4]], -2) == [[4, 3], [2, 1]]


def test_three_turns_is_one_turn_the_other_way() -> None:
    """Gives the anticlockwise turn for 3 and the clockwise turn for -3."""
    assert turned([[1, 2], [3, 4]], 3) == [[2, 4], [1, 3]]
    assert turned([[1, 2], [3, 4]], -3) == [[3, 1], [4, 2]]


def test_no_turns_changes_nothing() -> None:
    """Leaves the matrix as it was for zero turns."""
    assert turned(grid(4), 0) == grid(4)


def test_a_full_circle_changes_nothing() -> None:
    """Leaves the matrix as it was for four turns, or eight, or minus four."""
    assert turned(grid(3), 4) == grid(3)
    assert turned(grid(5), 8) == grid(5)
    assert turned(grid(4), -4) == grid(4)


def test_more_than_a_full_circle_keeps_the_remainder() -> None:
    """Turns by what is left after whole circles are removed."""
    assert turned([[1, 2], [3, 4]], 5) == [[3, 1], [4, 2]]
    assert turned([[1, 2], [3, 4]], 6) == [[4, 3], [2, 1]]
    assert turned([[1, 2], [3, 4]], -5) == [[2, 4], [1, 3]]
    assert turned([[1, 2], [3, 4]], -7) == [[3, 1], [4, 2]]


def test_handles_an_empty_matrix_and_a_single_cell() -> None:
    """Leaves a 0 x 0 and a 1 x 1 matrix alone for any number of turns."""
    for turns in (-2, -1, 0, 1, 2, 3):
        assert turned([], turns) == []
        assert turned([[7]], turns) == [[7]]


def test_keeps_the_row_lists_where_they_are() -> None:
    """Changes the contents of the caller's rows without moving or replacing them.

    Checked for all three rotations. A half turn done by reversing the outer
    list leaves the right values in the matrix and the wrong row object in
    every position.
    """
    for turns in (1, 2, 3):
        matrix = grid(3)
        rows = list(matrix)

        rotate(matrix, turns)

        assert all(now is before for now, before in zip(matrix, rows, strict=True)), (
            turns
        )
        assert matrix == stepped(grid(3), turns), turns


def test_agrees_with_turning_one_step_at_a_time() -> None:
    """Matches a step-by-step rotation for every size up to 6 and count from -9 to 9."""
    for n in range(7):
        for turns in range(-9, 10):
            assert turned(grid(n), turns) == stepped(grid(n), turns), (n, turns)


def test_opposite_turns_cancel() -> None:
    """Returns to the start after turning one way and then back by the same amount."""
    for turns in (1, 2, 3, 7, 10):
        matrix = grid(5)

        rotate(matrix, turns)
        rotate(matrix, -turns)

        assert matrix == grid(5), turns


def test_handles_a_thousand_million_turns() -> None:
    """Rotates by an enormous count without turning that many times.

    A thousand million is a multiple of four, so it is no turn at all; one
    more is a single clockwise turn, and one fewer a single anticlockwise
    turn. The same holds going the other way.
    """
    start = grid(6)

    assert turned(start, 10**9) == start
    assert turned(start, 10**9 + 1) == stepped(start, 1)
    assert turned(start, 10**9 - 1) == stepped(start, -1)
    assert turned(start, -(10**9)) == start
    assert turned(start, -(10**9) + 2) == stepped(start, 2)


def test_rotates_a_large_matrix() -> None:
    """Rotates a 300 x 300 matrix each of the three ways."""
    start = grid(300)

    for turns in (1, 2, -1):
        assert turned(start, turns) == stepped(start, turns), turns
