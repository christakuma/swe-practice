"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import count_islands


def test_counts_two_separate_islands() -> None:
    """Counts groups that do not touch as separate islands."""
    grid = [
        [1, 1, 0, 0],
        [1, 1, 0, 0],
        [0, 0, 1, 0],
    ]

    assert count_islands(grid) == 2


def test_counts_one_island_that_bends() -> None:
    """Follows a single island around two corners.

    A C-shape: the two arms are joined only by the right-hand column. A walk
    that explores in one direction, or that forgets to look upwards, finds two
    islands here.
    """
    grid = [
        [1, 1, 1],
        [0, 0, 1],
        [1, 1, 1],
    ]

    assert count_islands(grid) == 1


def test_does_not_connect_diagonally() -> None:
    """Treats diagonally touching cells as separate islands.

    The constraint most easily lost by generating neighbour offsets with two
    nested loops over -1, 0, 1. There are four neighbours, not eight.
    """
    grid = [
        [1, 0],
        [0, 1],
    ]

    assert count_islands(grid) == 2


def test_counts_a_grid_of_all_water() -> None:
    """Returns zero when there is no land."""
    assert count_islands([[0, 0], [0, 0]]) == 0


def test_counts_a_grid_of_all_land_as_one() -> None:
    """Returns one when every cell is connected."""
    assert count_islands([[1, 1], [1, 1]]) == 1


def test_handles_an_empty_grid() -> None:
    """Returns zero for no grid at all."""
    assert count_islands([]) == 0


def test_handles_a_grid_with_no_columns() -> None:
    """Returns zero for rows that hold nothing."""
    assert count_islands([[], []]) == 0


def test_handles_a_single_row() -> None:
    """Counts along one row, where the only neighbours are left and right."""
    assert count_islands([[1, 0, 1, 1, 0, 1]]) == 3


def test_handles_a_single_column() -> None:
    """Counts down one column."""
    assert count_islands([[1], [0], [1]]) == 2


def test_handles_a_large_connected_grid_quickly() -> None:
    """Walks one island of ninety thousand cells.

    A 300x300 grid of all land. A recursive flood fill hits Python's default
    recursion limit of 1000 frames long before it finishes; an explicit stack
    does not.
    """
    size = 300

    assert count_islands([[1] * size for _ in range(size)]) == 1
