"""Reference solution. CI asserts this passes every test in `tests.py`."""


def spiral_order(matrix: list[list[int]]) -> list[int]:
    """Return every value of `matrix` in spiral order.

    Four boundaries, not a grid of visited flags. `top` and `bottom` are the
    first and last rows still unread, `left` and `right` the first and last
    columns; each of the four passes consumes an entire edge and then moves its
    own boundary inward by one. Because every cell is consumed exactly once,
    the walk is O(m * n) and the only state is four integers.

    **The two inner guards are the whole problem.** On the last ring of a
    non-square matrix, one pass can consume an edge that another pass is about
    to consume again. With a single row left, the top pass reads it
    left-to-right and the bottom pass -- whose row index is now the same row --
    reads it back again, duplicating every value. Same for a single column and
    the left pass.

    `if top <= bottom` and `if left <= right` are checked *after* the earlier
    passes have moved their boundaries, so each asks the live question "is there
    still a distinct row/column here?" rather than a question about the
    original shape. A solution without them is correct on every square matrix,
    which is why square test cases cannot find the bug.
    """
    if not matrix or not matrix[0]:
        return []

    values: list[int] = []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1

    while top <= bottom and left <= right:
        for column in range(left, right + 1):
            values.append(matrix[top][column])
        top += 1

        for row in range(top, bottom + 1):
            values.append(matrix[row][right])
        right -= 1

        if top <= bottom:
            for column in range(right, left - 1, -1):
                values.append(matrix[bottom][column])
            bottom -= 1

        if left <= right:
            for row in range(bottom, top - 1, -1):
                values.append(matrix[row][left])
            left += 1

    return values
