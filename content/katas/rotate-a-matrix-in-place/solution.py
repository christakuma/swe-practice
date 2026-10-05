"""Reference solution. CI asserts this passes every test in `tests.py`."""


def rotate(matrix: list[list[int]]) -> None:
    """Rotate `matrix` 90 degrees clockwise, in place.

    Attacking the rotation directly means a four-way cycle -- each element
    displaces another, which displaces another, back to the start -- and the
    index arithmetic for the ring-by-ring version is genuinely easy to get
    wrong. The trick is to stop solving it directly and factor it into two
    operations that are each trivially correct:

        transpose, then reverse each row.

    Transposing reflects across the main diagonal; reversing each row reflects
    across the vertical centre line. Two reflections compose to a rotation, and
    these two particular reflections compose to a clockwise quarter turn. Track
    the top-left corner to see it: (0,0) is fixed by the transpose, then the
    row reversal sends it to (0, n-1), which is where a clockwise rotation puts
    it.

    `range(i + 1, n)` is the detail that matters. The transpose has to swap each
    pair *once*, so the inner loop covers only the entries strictly above the
    diagonal. Running `j` over the full row swaps every pair twice and the
    matrix comes back unchanged -- a bug that looks like nothing happened
    rather than like a wrong rotation.

    Both steps mutate through the existing row lists (`row.reverse()`, not
    `row[::-1]`), so no second grid is allocated and the caller's object is the
    one that changes.
    """
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    for row in matrix:
        row.reverse()
