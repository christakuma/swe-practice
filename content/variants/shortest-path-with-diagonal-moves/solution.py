"""Reference solution. CI asserts this passes every test in `tests.py`."""

from collections import deque


def shortest_path(grid: list[list[int]]) -> int:
    """Return the number of cells on the shortest route, moving in 8 directions.

    Breadth-first search, unchanged except for the neighbourhood. Every step
    costs one whichever way it goes, so the first time the destination is
    reached is by a shortest route. Cells are marked as walls when queued,
    which the prompt permits and which keeps each cell out of the queue a
    second time.
    """
    if not grid or grid[0][0] == 1 or grid[-1][-1] == 1:
        return -1
    last = (len(grid) - 1, len(grid[0]) - 1)
    queue = deque([(0, 0, 1)])
    grid[0][0] = 1
    while queue:
        y, x, cells = queue.popleft()
        if (y, x) == last:
            return cells
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]) and grid[ny][nx] == 0:
                    grid[ny][nx] = 1
                    queue.append((ny, nx, cells + 1))
    return -1
