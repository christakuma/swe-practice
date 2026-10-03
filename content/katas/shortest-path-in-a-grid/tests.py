"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import shortest_path


def test_crosses_an_open_grid() -> None:
    """Takes the straight route across an open grid."""
    grid = [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]

    assert shortest_path(grid) == 5


def test_goes_around_a_wall() -> None:
    """Finds the route around an obstacle."""
    grid = [
        [0, 1, 0],
        [0, 1, 0],
        [0, 0, 0],
    ]

    assert shortest_path(grid) == 5


def test_takes_the_shorter_of_two_routes() -> None:
    """Returns the shortest route when there are two ways round.

    The route over the top is nine cells and the one down the left is seven. A
    depth-first walk finds whichever it tries first and reports that.
    """
    grid = [
        [0, 0, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
    ]

    assert shortest_path(grid) == 6


def test_reports_no_route() -> None:
    """Returns -1 when the destination is walled off."""
    grid = [
        [0, 1],
        [1, 0],
    ]

    assert shortest_path(grid) == -1


def test_reports_no_route_when_the_start_is_a_wall() -> None:
    """Returns -1 when the start itself is blocked."""
    assert shortest_path([[1, 0], [0, 0]]) == -1


def test_reports_no_route_when_the_destination_is_a_wall() -> None:
    """Returns -1 when the destination itself is blocked."""
    assert shortest_path([[0, 0], [0, 1]]) == -1


def test_handles_a_single_open_cell() -> None:
    """Counts the start as one step when it is also the destination."""
    assert shortest_path([[0]]) == 1


def test_handles_an_empty_grid() -> None:
    """Returns -1 for no grid at all."""
    assert shortest_path([]) == -1


def test_handles_a_corridor() -> None:
    """Follows a one-cell-wide corridor that doubles back."""
    grid = [
        [0, 0, 0, 0, 0],
        [1, 1, 1, 1, 0],
        [0, 0, 0, 0, 0],
    ]

    assert shortest_path(grid) == 7


def test_crosses_a_large_open_grid_quickly() -> None:
    """Crosses a grid with a great many equally short routes.

    A 200x200 open grid: the shortest route is 399 cells and there are
    astronomically many of them. A search that marks cells as seen only when it
    takes them off the queue enqueues each cell once per neighbour, and a
    search that keeps looking for shorter routes never finishes.
    """
    size = 200
    grid = [[0] * size for _ in range(size)]

    assert shortest_path(grid) == 2 * size - 1
