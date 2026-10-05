"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_paths(width: int, height: int) -> int:
    """Count right/down paths across a grid.

    You can only arrive at a cell from the one above it or the one to its left,
    so the number of ways to reach it is the sum of those two. The top row and
    left column have exactly one way each -- straight along the edge -- and
    that is the whole recurrence.

    The table is filled row by row because that ordering makes every dependency
    already final: the cell above is in the previous row, the cell to the left
    is earlier in this one. Same argument as in
    `count-bits-for-every-number-up-to-n` -- dynamic programming is an ordering
    in which the subproblems you need are behind you.

    **One row is enough, and the in-place update is the interesting line.**

        row[column] += row[column - 1]

    Before the assignment, `row[column]` still holds the *previous* row's value
    for this column -- which is the cell above -- and `row[column - 1]` has
    already been updated this pass, so it is the cell to the left. One array,
    overwritten left to right, and both operands mean the right thing at the
    moment they are read. Reverse the iteration and `row[column - 1]` would
    still be the old row, giving the wrong neighbour.

    Iterating over `min(width, height)` keeps the stored row the shorter
    dimension, since the answer is symmetric: a path is a sequence of moves and
    swapping the axes just relabels them.

    There is also a closed form. A path is exactly a choice of which of the
    `(width - 1) + (height - 1)` moves are "down", so the answer is
    `comb(width + height - 2, height - 1)` -- O(min(m, n)) arithmetic and no
    table at all. The table is written out here because the recurrence
    generalises to grids with obstacles or weights, and the binomial does not.
    """
    if width <= 0 or height <= 0:
        return 0

    short, long = min(width, height), max(width, height)
    row = [1] * short
    for _ in range(long - 1):
        for column in range(1, short):
            row[column] += row[column - 1]
    return row[-1]
