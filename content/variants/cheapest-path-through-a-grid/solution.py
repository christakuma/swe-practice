"""Reference solution. CI asserts this passes every test in `tests.py`."""

import math


def cheapest_path(grid: list[list[int]]) -> int:
    """Return the smallest total cost of a right-and-down path across the grid.

    The path-counting table with `min` in place of the sum: the cheapest way
    into a cell is its own cost plus the cheaper of the cell above and the
    cell to the left. One row of the table is kept and overwritten, so before
    `best[column]` is updated it still holds the value from the row above.

    Outside the grid is infinitely expensive, not free. The one exception is
    the starting cell, which nothing leads into: it gets a 0 to add its own
    cost to, placed where the first cell will look for its neighbour above.
    """
    best: list[float] = [math.inf] * len(grid[0])
    best[0] = 0
    for row in grid:
        left = math.inf
        for column, cost in enumerate(row):
            best[column] = left = cost + min(best[column], left)
    return int(best[-1])
