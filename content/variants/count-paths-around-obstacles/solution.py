"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_paths(grid: list[list[int]]) -> int:
    """Count right/down paths across a grid that avoid blocked cells.

    One row of the table, updated in place. `ways[column]` holds the count
    for the cell above until it is overwritten, and `ways[column - 1]` has
    already been updated to the cell on the left, so adding them gives the
    new cell. A blocked cell is set to zero, which is all that is needed for
    it to block: the cells after it add nothing from it.
    """
    if not grid or not grid[0]:
        return 0
    ways = [0] * len(grid[0])
    ways[0] = 1
    for line in grid:
        for column, cell in enumerate(line):
            if cell == 1:
                ways[column] = 0
            elif column > 0:
                ways[column] += ways[column - 1]
    return ways[-1]
