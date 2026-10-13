"""Reference solution. CI asserts this passes every test in `tests.py`."""


def set_zeroes(matrix: list[list[int]]) -> int:
    """Zero the row and column of every original zero, and count the changes.

    The rows and columns to clear are collected first, from the matrix as it
    arrived, so that zeros written later cannot trigger more clearing. Each
    cell is then visited exactly once, which is what makes the count right
    without any correction for overlaps: a cell is counted when, and only
    when, it is actually overwritten with a zero it did not already hold.
    """
    rows = {y for y, line in enumerate(matrix) if 0 in line}
    columns = {x for line in matrix for x, value in enumerate(line) if value == 0}
    changed = 0
    for y, line in enumerate(matrix):
        for x, value in enumerate(line):
            if value != 0 and (y in rows or x in columns):
                line[x] = 0
                changed += 1
    return changed
