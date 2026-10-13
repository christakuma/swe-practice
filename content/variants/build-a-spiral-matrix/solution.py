"""Reference solution. CI asserts this passes every test in `tests.py`."""


def spiral_matrix(n: int) -> list[list[int]]:
    """Return an `n x n` matrix holding 1..n*n in clockwise spiral order.

    The same four boundaries as reading a spiral, closing in after each side
    is walked. Reading an arbitrary matrix needs a guard before the bottom
    and left passes, for the ring that has collapsed to a single row or
    column. A square never produces one: its rings close on all four sides
    at once, and when the last ring is a single cell the remaining three
    passes are over empty ranges. So there are no guards here: a version
    with them and a version without behave identically on every square.
    """
    matrix = [[0] * n for _ in range(n)]
    top, bottom, left, right = 0, n - 1, 0, n - 1
    value = 1
    while top <= bottom and left <= right:
        for column in range(left, right + 1):
            matrix[top][column] = value
            value += 1
        top += 1
        for row in range(top, bottom + 1):
            matrix[row][right] = value
            value += 1
        right -= 1
        for column in range(right, left - 1, -1):
            matrix[bottom][column] = value
            value += 1
        bottom -= 1
        for row in range(bottom, top - 1, -1):
            matrix[row][left] = value
            value += 1
        left += 1
    return matrix
