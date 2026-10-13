"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import neither_ocean


def reaches_an_edge(heights: list[list[int]], start: tuple[int, int]) -> bool:
    """Flow downhill from one cell and see whether any edge is reached."""
    rows, columns = len(heights), len(heights[0])
    seen, frontier = {start}, [start]
    while frontier:
        y, x = frontier.pop()
        if y in (0, rows - 1) or x in (0, columns - 1):
            return True
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if (ny, nx) not in seen and heights[ny][nx] <= heights[y][x]:
                seen.add((ny, nx))
                frontier.append((ny, nx))
    return False


def by_flowing(heights: list[list[int]]) -> list[tuple[int, int]]:
    return [
        (y, x)
        for y in range(len(heights))
        for x in range(len(heights[0]))
        if not reaches_an_edge(heights, (y, x))
    ]


def test_finds_a_pit() -> None:
    """Returns a cell lower than all four of its neighbours."""
    assert neither_ocean([[5, 5, 5], [5, 1, 5], [5, 5, 5]]) == [(1, 1)]


def test_finds_a_basin_of_several_cells() -> None:
    """Returns every cell of a flat basin, sorted."""
    heights = [[9, 9, 9, 9], [9, 0, 0, 9], [9, 9, 9, 9]]

    assert neither_ocean(heights) == [(1, 1), (1, 2)]


def test_returns_nothing_when_everything_drains() -> None:
    """Returns an empty list when every cell reaches an ocean."""
    assert neither_ocean([[1, 2, 2, 3], [3, 2, 3, 4], [2, 4, 5, 3]]) == []
    assert neither_ocean([[4, 4, 4], [4, 4, 4], [4, 4, 4]]) == []


def test_a_basin_with_a_way_out_is_not_trapped() -> None:
    """Does not return a low cell that can flow out across a level path."""
    heights = [[5, 5, 5], [5, 1, 1], [5, 5, 5]]

    assert neither_ocean(heights) == []


def test_handles_small_and_empty_grids() -> None:
    """Returns nothing for grids with no interior, and for no grid."""
    assert neither_ocean([]) == []
    assert neither_ocean([[]]) == []
    assert neither_ocean([[3]]) == []
    assert neither_ocean([[3, 1, 3], [3, 1, 3]]) == []


def test_leaves_the_heights_alone() -> None:
    """Does not modify the grid it was given."""
    heights = [[5, 5, 5], [5, 1, 5], [5, 5, 5]]

    neither_ocean(heights)

    assert heights == [[5, 5, 5], [5, 1, 5], [5, 5, 5]]


def test_agrees_with_flowing_from_every_cell() -> None:
    """Matches a downhill search from every cell, for every small grid."""
    for cells in product(range(3), repeat=9):
        heights = [list(cells[y * 3 : y * 3 + 3]) for y in range(3)]
        assert neither_ocean(heights) == by_flowing(heights), heights
    for cells in product(range(2), repeat=12):
        heights = [list(cells[y * 4 : y * 4 + 4]) for y in range(3)]
        assert neither_ocean(heights) == by_flowing(heights), heights


def test_handles_a_large_basin() -> None:
    """Handles a 200x200 grid with one enormous basin within the time limit."""
    side = 200
    heights = (
        [[9] * side]
        + [[9, *([0] * (side - 2)), 9] for _ in range(side - 2)]
        + [[9] * side]
    )

    assert len(neither_ocean(heights)) == (side - 2) ** 2
