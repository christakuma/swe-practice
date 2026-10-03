"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_islands(grid: list[list[int]]) -> int:
    """Count the connected groups of 1s in a grid.

    A grid is a graph: each cell is a node, adjacency is an edge. Once that is
    said, the problem is the textbook one -- count connected components -- and
    the answer is to walk from every unvisited node and count how many walks it
    takes to cover everything.

    Sinking the island (writing 0 over each visited cell) instead of keeping a
    visited set is the standard move here and worth being deliberate about: it
    is O(1) extra space rather than O(n), and it destroys the caller's grid. That
    is a licence this kata grants explicitly, and in real code it is the kind of
    thing to grant explicitly too rather than assume.

    Iterative with an explicit stack, not recursive. A 300x300 grid of all 1s is
    ninety thousand connected cells, and a recursive flood fill reaches Python's
    1000-frame limit about 1% of the way in. That is not a theoretical concern:
    the long test in this kata is exactly that grid.
    """
    if not grid or not grid[0]:
        return 0

    rows, columns = len(grid), len(grid[0])
    islands = 0

    for row in range(rows):
        for column in range(columns):
            if grid[row][column] != 1:
                continue
            islands += 1
            stack = [(row, column)]
            grid[row][column] = 0
            while stack:
                this_row, this_column = stack.pop()
                for next_row, next_column in (
                    (this_row - 1, this_column),
                    (this_row + 1, this_column),
                    (this_row, this_column - 1),
                    (this_row, this_column + 1),
                ):
                    if (
                        0 <= next_row < rows
                        and 0 <= next_column < columns
                        and grid[next_row][next_column] == 1
                    ):
                        grid[next_row][next_column] = 0
                        stack.append((next_row, next_column))
    return islands
