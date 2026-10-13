"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import count_islands


def enclosed_by_labelling(grid: list[list[int]]) -> int:
    """Label every island, then count the labels that never touch the edge."""
    rows, columns = len(grid), len(grid[0])
    label: dict[tuple[int, int], int] = {}
    touching: set[int] = set()
    islands = 0
    for start in product(range(rows), range(columns)):
        if grid[start[0]][start[1]] == 0 or start in label:
            continue
        islands += 1
        label[start] = islands
        queue = [start]
        for row, column in queue:
            if row in (0, rows - 1) or column in (0, columns - 1):
                touching.add(islands)
            for cell in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                inside = 0 <= cell[0] < rows and 0 <= cell[1] < columns
                if inside and grid[cell[0]][cell[1]] == 1 and cell not in label:
                    label[cell] = islands
                    queue.append(cell)
    return islands - len(touching)


def test_counts_an_island_surrounded_by_water() -> None:
    """Counts an island with water on every side."""
    grid = [
        [0, 0, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
    ]

    assert count_islands(grid) == 1


def test_does_not_count_an_island_on_any_edge() -> None:
    """Ignores islands on the top, bottom, left and right edges."""
    for row, column in ((0, 2), (4, 2), (2, 0), (2, 4)):
        grid = [[0] * 5 for _ in range(5)]
        grid[row][column] = 1

        assert count_islands(grid) == 0, (row, column)


def test_an_island_reaching_in_from_the_side() -> None:
    """Ignores islands that run inland from the left and right edges."""
    from_the_left = [[0, 0, 0, 0], [1, 1, 1, 0], [0, 0, 0, 0]]
    from_the_right = [[0, 0, 0, 0], [0, 1, 1, 1], [0, 0, 0, 0]]

    assert count_islands(from_the_left) == 0
    assert count_islands(from_the_right) == 0


def test_counts_only_the_enclosed_islands() -> None:
    """Counts the enclosed islands among others that touch the edge."""
    grid = [
        [1, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0, 1],
        [0, 0, 0, 0, 0, 0],
    ]

    assert count_islands(grid) == 3


def test_one_edge_cell_disqualifies_the_whole_island() -> None:
    """Ignores an island that starts inland and reaches the edge later.

    Scanning row by row, the first cell found is in the middle of the grid;
    the island only reaches the bottom edge at the end of its tail.
    """
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 1, 0],
    ]

    assert count_islands(grid) == 0


def test_an_island_on_the_edge_is_not_counted_in_pieces() -> None:
    """Does not count the rest of an island after finding its edge cell.

    The island is met at the top edge first. Giving up on it there, without
    marking the cells below, leaves them to be found and counted afterwards.
    """
    grid = [
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
    ]

    assert count_islands(grid) == 0


def test_a_ring_of_land_around_a_lake() -> None:
    """Ignores a ring on the edge and counts an island in its lake."""
    ring = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]
    with_island = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 1, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
    ]

    assert count_islands(ring) == 0
    assert count_islands(with_island) == 1


def test_diagonal_cells_are_not_connected() -> None:
    """Counts an inland cell that touches an edge island only at a corner."""
    grid = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 0],
    ]

    assert count_islands(grid) == 1


def test_grids_too_thin_to_have_an_inside() -> None:
    """Returns 0 for empty grids and grids one or two cells across."""
    assert count_islands([]) == 0
    assert count_islands([[]]) == 0
    assert count_islands([[1]]) == 0
    assert count_islands([[1, 0, 1, 1]]) == 0
    assert count_islands([[1, 1], [1, 1], [0, 1]]) == 0


def test_agrees_with_labelling_on_every_small_grid() -> None:
    """Matches a label-then-check count for every 3 x 5 grid."""
    enclosed = 0
    for cells in product((0, 1), repeat=15):
        grid = [list(cells[row * 5 : row * 5 + 5]) for row in range(3)]
        expected = enclosed_by_labelling(grid)
        assert count_islands([list(row) for row in grid]) == expected, grid
        enclosed += expected
    assert enclosed > 1000


def test_handles_one_island_covering_a_large_grid() -> None:
    """Handles 90,000 cells of land without recursing.

    Solid land is one island on the edge. With a moat of water one cell in
    from the border, the middle becomes a second island that counts.
    """
    solid = [[1] * 300 for _ in range(300)]
    moated = [[1] * 300 for _ in range(300)]
    for index in range(1, 299):
        moated[1][index] = moated[298][index] = 0
        moated[index][1] = moated[index][298] = 0

    assert count_islands(solid) == 0
    assert count_islands(moated) == 1
