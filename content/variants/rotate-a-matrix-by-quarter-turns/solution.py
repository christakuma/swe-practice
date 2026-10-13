"""Reference solution. CI asserts this passes every test in `tests.py`."""

FULL_CIRCLE = 4
HALF_TURN = 2
CLOCKWISE = 1


def rotate(matrix: list[list[int]], turns: int) -> None:
    """Rotate `matrix` by `turns` quarter turns, in place.

    Four turns restore the matrix, so the count is reduced modulo 4 and one
    of four things happens. Python's `%` takes the sign of the divisor, so a
    negative count lands on 1, 2 or 3 without help: one turn anticlockwise is
    three clockwise, and `-1 % 4` is 3.

    Each of the three real rotations is two reflections, drawn from the
    transpose, the left-to-right flip and the top-to-bottom flip:

    - clockwise is the transpose, then left-to-right;
    - anticlockwise is the transpose, then top-to-bottom;
    - a half turn is the two flips, and no transpose.

    Doing the clockwise turn `turns % 4` times would also be right and at
    most three times the work. The reflections are used because they make
    the half turn and the anticlockwise turn as cheap as the clockwise one,
    and because each reflection is a loop that is hard to get wrong.

    The top-to-bottom flip swaps values between rows, not the rows
    themselves. `matrix.reverse()` would be one line and would leave the
    caller's first row list sitting at the bottom of the matrix.
    """
    turns %= FULL_CIRCLE
    if turns == 0:
        return
    if turns == HALF_TURN:
        _flip_left_to_right(matrix)
        _flip_top_to_bottom(matrix)
        return
    _transpose(matrix)
    if turns == CLOCKWISE:
        _flip_left_to_right(matrix)
    else:
        _flip_top_to_bottom(matrix)


def _transpose(matrix: list[list[int]]) -> None:
    """Reflect across the main diagonal: rows become columns."""
    for row in range(len(matrix)):
        for column in range(row + 1, len(matrix)):
            matrix[row][column], matrix[column][row] = (
                matrix[column][row],
                matrix[row][column],
            )


def _flip_left_to_right(matrix: list[list[int]]) -> None:
    """Reverse every row where it stands."""
    for row in matrix:
        row.reverse()


def _flip_top_to_bottom(matrix: list[list[int]]) -> None:
    """Exchange the contents of each row with its mirror image's."""
    size = len(matrix)
    for top in range(size // 2):
        upper, lower = matrix[top], matrix[size - 1 - top]
        for column in range(size):
            upper[column], lower[column] = lower[column], upper[column]
