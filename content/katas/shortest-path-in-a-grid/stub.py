"""Your solution goes here. The tests import `shortest_path` from here."""


def shortest_path(grid: list[list[int]]) -> int:
    """Return the fewest steps from the top-left cell to the bottom-right.

    A step moves to a cell directly above, below, left or right. A cell holding
    1 is a wall and cannot be entered.

    Args:
        grid: a rectangular grid of 0s (open) and 1s (wall).

    Returns:
        The number of cells on the shortest route, counting both ends, or -1 if
        there is no route. A 1x1 open grid is 1 step.
    """
    raise NotImplementedError
