"""Reference solution. CI asserts this passes every test in `tests.py`."""

from collections import deque


def shortest_path(grid: list[list[int]]) -> int:
    """Return the fewest steps from the top-left cell to the bottom-right.

    Breadth-first search, and the reason it has to be breadth-first is the whole
    point: BFS reaches every cell by the fewest steps, because it finishes all of
    distance d before it starts any of distance d + 1. Depth-first search reaches
    the same cells by whichever route it wandered down, so it finds *a* path and
    not the shortest -- and correcting it means revisiting cells whenever a
    shorter route shows up, which is a different and much slower algorithm.

    Marking a cell as seen when it is **enqueued**, not when it is dequeued, is
    the detail that matters. Marking on dequeue lets a cell enter the queue once
    per neighbour that reaches it, which multiplies the work by the branching
    factor and -- in a grid with many equal-length paths -- is the difference
    between linear and badly superlinear.

    The distance travels in the queue rather than in a parallel grid, because
    nothing here needs to look a distance up again. If the problem also wanted
    the route, the thing to carry would be a predecessor per cell instead.
    """
    if not grid or not grid[0]:
        return -1
    rows, columns = len(grid), len(grid[0])
    if grid[0][0] == 1 or grid[rows - 1][columns - 1] == 1:
        return -1

    queue: deque[tuple[int, int, int]] = deque([(0, 0, 1)])
    grid[0][0] = 1

    while queue:
        row, column, steps = queue.popleft()
        if row == rows - 1 and column == columns - 1:
            return steps
        for next_row, next_column in (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        ):
            if (
                0 <= next_row < rows
                and 0 <= next_column < columns
                and grid[next_row][next_column] == 0
            ):
                grid[next_row][next_column] = 1
                queue.append((next_row, next_column, steps + 1))
    return -1
