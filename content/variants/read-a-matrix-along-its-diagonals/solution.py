"""Reference solution. CI asserts this passes every test in `tests.py`."""


def diagonal_order(matrix: list[list[int]]) -> list[int]:
    """Return the matrix's elements in diagonal zigzag order.

    Every cell on one anti-diagonal has the same `row + column`, so the
    diagonals are numbered by that sum, from 0 at the top-left corner to
    `rows + columns - 2` at the bottom-right.

    Each diagonal is gathered with its rows ascending -- which is the
    down-and-left direction -- and the even-numbered ones are then reversed,
    because those are the ones the zigzag travels up and to the right.

    The row range is clipped at both ends so that the column, `d - row`,
    stays inside the matrix. That clipping is all a non-square matrix needs.
    """
    if not matrix or not matrix[0]:
        return []
    rows, columns = len(matrix), len(matrix[0])
    order: list[int] = []
    for diagonal in range(rows + columns - 1):
        first_row = max(0, diagonal - columns + 1)
        last_row = min(diagonal, rows - 1)
        cells = [matrix[row][diagonal - row] for row in range(first_row, last_row + 1)]
        if diagonal % 2 == 0:
            cells.reverse()
        order.extend(cells)
    return order
