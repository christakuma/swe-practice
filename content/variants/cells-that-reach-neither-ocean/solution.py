"""Reference solution. CI asserts this passes every test in `tests.py`."""


def neither_ocean(heights: list[list[int]]) -> list[tuple[int, int]]:
    """Return the cells from which water reaches neither ocean.

    A cell is trapped exactly when no edge can be reached by flowing
    downhill from it. Searching backwards -- from every edge cell, uphill or
    level -- marks each cell that *can* drain; the trapped cells are the
    rest. Which ocean an edge belongs to does not matter for this question,
    so all four edges seed a single search.
    """
    if not heights or not heights[0]:
        return []
    rows, columns = len(heights), len(heights[0])
    drains = [[False] * columns for _ in range(rows)]
    stack = [
        (y, x)
        for y in range(rows)
        for x in range(columns)
        if y in (0, rows - 1) or x in (0, columns - 1)
    ]
    for y, x in stack:
        drains[y][x] = True
    while stack:
        y, x = stack.pop()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if (
                0 <= ny < rows
                and 0 <= nx < columns
                and not drains[ny][nx]
                and heights[ny][nx] >= heights[y][x]
            ):
                drains[ny][nx] = True
                stack.append((ny, nx))
    return [(y, x) for y in range(rows) for x in range(columns) if not drains[y][x]]
