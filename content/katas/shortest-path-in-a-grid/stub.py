"""Your solution goes here. The tests import `shortest_path` from here."""


def shortest_path(grid: list[list[int]]) -> int:
    """Return the number of cells on the shortest route across the grid.

    The route runs from the top-left cell to the bottom-right, moving each time
    to a cell directly above, below, left or right. A cell holding 1 is a wall
    and cannot be entered.

    Args:
        grid: a rectangular grid of 0s (open) and 1s (wall). May be empty.

    Returns:
        How many cells the shortest route visits, counting both ends, or -1 if
        there is no route. A 1x1 open grid is 1.
    """
    raise NotImplementedError
