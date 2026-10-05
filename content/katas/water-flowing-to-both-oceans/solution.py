"""Reference solution. CI asserts this passes every test in `tests.py`."""

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def both_oceans(heights: list[list[int]]) -> list[tuple[int, int]]:
    """Return the cells from which water reaches both oceans.

    Searching downhill from each cell asks "can water escape from here?" once
    per cell, and each search can cover the whole grid -- O((m*n)^2), with
    almost all of it repeated.

    **The move is to reverse the question.** Instead of asking which cells
    reach the ocean, ask which cells *the ocean can reach*, walking uphill from
    the borders. Uphill is the exact reverse of the flow rule: water runs from
    a cell to a neighbour at the same height or lower, so the reverse walk goes
    to a neighbour at the same height or higher. Everything reachable that way
    from an edge is a cell that can drain to that edge.

    Two searches, one per ocean, each seeded with its **whole border** rather
    than a single starting point -- a multi-source search, which costs nothing
    extra because the visited set is shared across all the sources. Each search
    visits every cell at most once, so the whole thing is O(m*n), and the
    answer is the intersection of the two reachable sets.

    `>=` is what makes a plateau work. Equal heights flow both ways, so a flat
    region is fully connected and a flat grid drains everywhere. Using `>`
    would strand every plateau that does not strictly rise, which on a flat
    grid means returning only the border.

    The iterative stack matters at this size: a 200x200 grid is 40,000 cells
    and a snaking uphill path through it would blow the recursion limit long
    before the time limit.
    """
    if not heights or not heights[0]:
        return []

    rows, columns = len(heights), len(heights[0])

    def reachable(sources: list[tuple[int, int]]) -> set[tuple[int, int]]:
        seen = set(sources)
        stack = list(sources)
        while stack:
            row, column = stack.pop()
            for row_step, column_step in STEPS:
                next_row, next_column = row + row_step, column + column_step
                if not (0 <= next_row < rows and 0 <= next_column < columns):
                    continue
                if (next_row, next_column) in seen:
                    continue
                # Uphill: the reverse of "flows to an equal-or-lower neighbour".
                if heights[next_row][next_column] < heights[row][column]:
                    continue
                seen.add((next_row, next_column))
                stack.append((next_row, next_column))
        return seen

    top_left = [(0, column) for column in range(columns)]
    top_left += [(row, 0) for row in range(rows)]
    bottom_right = [(rows - 1, column) for column in range(columns)]
    bottom_right += [(row, columns - 1) for row in range(rows)]

    return sorted(reachable(top_left) & reachable(bottom_right))
