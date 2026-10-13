"""Reference solution. CI asserts this passes every test in `tests.py`."""


def set_zeroes(matrix: list[list[int]]) -> None:
    """Zero the row, column and diagonals of every original zero, in place.

    A cell lies on four lines, and each line has a number that every cell on
    it shares: its row, its column, `row - column` for the diagonal that
    falls to the right, and `row + column` for the one that falls to the
    left. So four lists of flags record everything the first pass learns,
    and the second pass clears a cell if any of its four lines is flagged.

    Two passes are what keep written zeros from counting. Nothing is
    written until every original zero has been seen.

    `row - column` is negative above the main diagonal. It is shifted by
    `columns - 1` to index from zero, and that shift is not a nicety: a
    negative index into a Python list is legal and reads from the far end,
    so an unshifted list sized for the larger dimension would run without
    error and treat two different diagonals as one.

    The flags are `m + n` booleans four times over. The standard problem's
    constant-space trick stores its flags in the first row and column, which
    have `m + n - 1` cells between them; that is enough for the rows and
    columns and leaves nowhere for `2 * (m + n - 1)` diagonals.
    """
    rows = len(matrix)
    columns = len(matrix[0]) if rows else 0

    row_hit = [False] * rows
    column_hit = [False] * columns
    falling_hit = [False] * (rows + columns)
    rising_hit = [False] * (rows + columns)

    for row in range(rows):
        for column in range(columns):
            if matrix[row][column] == 0:
                row_hit[row] = True
                column_hit[column] = True
                falling_hit[row - column + columns - 1] = True
                rising_hit[row + column] = True

    for row in range(rows):
        cells = matrix[row]
        for column in range(columns):
            if (
                row_hit[row]
                or column_hit[column]
                or falling_hit[row - column + columns - 1]
                or rising_hit[row + column]
            ):
                cells[column] = 0
