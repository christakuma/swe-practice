"""Reference solution. CI asserts this passes every test in `tests.py`."""


def rotate(matrix: list[list[int]]) -> None:
    """Rotate `matrix` 90 degrees anticlockwise, in place.

    Transpose, then reverse the order of the rows. The transpose swaps each
    pair of cells across the main diagonal; reversing the rows then carries
    what was the last column to the top. Reversing each row instead would
    give the clockwise turn -- the two directions differ by which mirror
    follows the transpose.
    """
    size = len(matrix)
    for row in range(size):
        for column in range(row + 1, size):
            matrix[row][column], matrix[column][row] = (
                matrix[column][row],
                matrix[row][column],
            )
    matrix.reverse()
