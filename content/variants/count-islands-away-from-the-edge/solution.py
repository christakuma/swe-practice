"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_islands(grid: list[list[int]]) -> int:
    """Count the islands that do not touch the edge of the grid.

    Sink the disqualified islands first, then count what is left. A fill
    started from every land cell on the border removes exactly the islands
    that touch it -- all of each one, since a fill does not stop until the
    island is gone. After that every remaining `1` belongs to an enclosed
    island, and the ordinary count applies unchanged.

    Deciding per island instead -- explore it, remember whether an edge cell
    turned up -- works too, and has one trap this ordering avoids: stopping
    the exploration at the first edge cell leaves the rest of the island
    behind to be found again later and counted.

    The fill uses an explicit stack. One island can be the whole grid.
    """
    if not grid or not grid[0]:
        return 0
    rows, columns = len(grid), len(grid[0])

    def sink(row: int, column: int) -> None:
        grid[row][column] = 0
        stack = [(row, column)]
        while stack:
            r, c = stack.pop()
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= nr < rows and 0 <= nc < columns and grid[nr][nc] == 1:
                    grid[nr][nc] = 0
                    stack.append((nr, nc))

    for row in range(rows):
        for column in range(columns):
            on_edge = row in (0, rows - 1) or column in (0, columns - 1)
            if on_edge and grid[row][column] == 1:
                sink(row, column)

    enclosed = 0
    for row in range(1, rows - 1):
        for column in range(1, columns - 1):
            if grid[row][column] == 1:
                enclosed += 1
                sink(row, column)
    return enclosed
