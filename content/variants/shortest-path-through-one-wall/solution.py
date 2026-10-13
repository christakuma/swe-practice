"""Reference solution. CI asserts this passes every test in `tests.py`."""

from collections import deque


def shortest_path(grid: list[list[int]]) -> int:
    """Return the fewest cells on a route that passes through at most one wall.

    Breadth-first search, over states rather than cells. A state is a cell
    together with how many walls the route has entered so far, 0 or 1. Two
    routes to the same cell are interchangeable only if they have also spent
    the same number of breaks -- one that still has its break can do things
    the other cannot -- so "visited" is recorded per state.

    The grid's own values are the cost of entering a cell: 0 for open, 1 for
    a wall. That makes the start no special case. It is entered with whatever
    its value is, and a wall there simply begins the search with the break
    already spent.

    Every move costs one step whatever it enters, so the first time the
    destination is dequeued, in either state, is the shortest route.
    """
    if not grid or not grid[0]:
        return -1
    rows, columns = len(grid), len(grid[0])
    start = (0, 0, grid[0][0])
    seen = {start}
    queue = deque([(start, 1)])
    while queue:
        (row, column, used), cells = queue.popleft()
        if (row, column) == (rows - 1, columns - 1):
            return cells
        for r, c in (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        ):
            if not (0 <= r < rows and 0 <= c < columns):
                continue
            state = (r, c, used + grid[r][c])
            if state[2] <= 1 and state not in seen:
                seen.add(state)
                queue.append((state, cells + 1))
    return -1
