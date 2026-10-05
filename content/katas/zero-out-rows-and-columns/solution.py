"""Reference solution. CI asserts this passes every test in `tests.py`."""


def set_zeroes(matrix: list[list[int]]) -> None:
    """Zero the row and column of every original zero, in place.

    Clearing as you scan cannot work: a zero you write is indistinguishable
    from a zero you were looking for, so the clearing cascades and the whole
    matrix ends up zero. The operation has to be split into *record* and
    *write*, and the only question is where the record lives.

    A set of row indices and a set of column indices is the honest answer and
    costs O(m + n). To get to O(1), notice that what is needed is one flag per
    row and one per column -- and the matrix already contains a strip of
    exactly that shape, its own first row and first column. Use them as the
    notebook.

    `(0, 0)` is the one cell that would have to mean two things: "row 0 has a
    zero" and "column 0 has a zero". So column 0 gets its own ordinary
    variable, `clear_first_column`, and `(0, 0)` is left to speak only for row
    zero. One scalar is the entire O(1) overhead.

    Order is the other half. The interior is written from the markers *before*
    the marker strip is itself cleared, because zeroing a marker destroys what
    it was recording. And the interior scan starts at (1, 1): reading the
    markers as if they were data re-triggers on them and cascades exactly as
    the naive version does.
    """
    if not matrix or not matrix[0]:
        return

    rows, columns = len(matrix), len(matrix[0])
    clear_first_column = False

    for row in range(rows):
        if matrix[row][0] == 0:
            clear_first_column = True
        for column in range(1, columns):
            if matrix[row][column] == 0:
                matrix[row][0] = 0
                matrix[0][column] = 0

    # The interior, from the markers -- before the markers are overwritten.
    for row in range(1, rows):
        for column in range(1, columns):
            if matrix[row][0] == 0 or matrix[0][column] == 0:
                matrix[row][column] = 0

    # Only now, and only in this order: row zero before column zero would lose
    # the (0, 0) marker that row zero depends on.
    if matrix[0][0] == 0:
        for column in range(columns):
            matrix[0][column] = 0

    if clear_first_column:
        for row in range(rows):
            matrix[row][0] = 0
