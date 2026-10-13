"""Reference solution. CI asserts this passes every test in `tests.py`."""


def largest_island(grid: list[list[int]]) -> int:
    """Return the number of cells in the largest connected group of 1s.

    An explicit stack, because one island may be ninety thousand cells and
    recursion stops well short of that. A cell is sunk to 0 at the moment it
    is pushed, not when it is popped: that is what guarantees each cell goes
    on the stack once, so counting the pops counts the cells.
    """
    best = 0
    for top, row in enumerate(grid):
        for left, cell in enumerate(row):
            if cell != 1:
                continue
            grid[top][left] = 0
            stack = [(top, left)]
            area = 0
            while stack:
                y, x = stack.pop()
                area += 1
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < len(grid) and 0 <= nx < len(row) and grid[ny][nx] == 1:
                        grid[ny][nx] = 0
                        stack.append((ny, nx))
            best = max(best, area)
    return best
