"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from math import comb

from solution import count_paths


def reference(width: int, height: int) -> int:
    """The binomial closed form -- an independent oracle.

    A path is a choice of which moves are "down", so the count is a binomial
    coefficient. It shares no table, no recurrence and no loop with the
    intended solution.
    """
    if width <= 0 or height <= 0:
        return 0
    return comb(width + height - 2, height - 1)


def test_handles_the_worked_examples() -> None:
    """Returns the documented counts."""
    assert count_paths(3, 2) == 3
    assert count_paths(3, 7) == 28


def test_handles_a_single_cell() -> None:
    """Returns 1 for a 1x1 grid, where the start is the finish."""
    assert count_paths(1, 1) == 1


def test_handles_a_single_row_or_column() -> None:
    """Returns 1 when there is only one way across."""
    assert count_paths(1, 5) == 1
    assert count_paths(5, 1) == 1
    assert count_paths(1, 100) == 1


def test_handles_an_empty_grid() -> None:
    """Returns 0 when either dimension is zero."""
    assert count_paths(0, 5) == 0
    assert count_paths(5, 0) == 0
    assert count_paths(0, 0) == 0


def test_is_symmetric() -> None:
    """Gives the same answer with the dimensions swapped.

    A path is a sequence of moves and swapping the axes relabels them, so the
    count cannot depend on which dimension is which. This catches a solution
    that stores the wrong row when it picks the shorter dimension.
    """
    for width in range(1, 15):
        for height in range(1, 15):
            assert count_paths(width, height) == count_paths(height, width), (
                width,
                height,
            )


def test_handles_a_square_grid() -> None:
    """Returns the central binomial coefficients for square grids."""
    assert count_paths(2, 2) == 2
    assert count_paths(3, 3) == 6
    assert count_paths(4, 4) == 20
    assert count_paths(5, 5) == 70


def test_agrees_with_the_closed_form_across_many_sizes() -> None:
    """Matches the binomial coefficient for every grid up to 40 by 40.

    Sixteen hundred sizes. The in-place row update is the only subtle part --
    iterating the row in the wrong direction reads the already-updated
    neighbour as the cell above -- and it goes wrong at every size, which a
    single spot check would also catch but not localise.
    """
    for width in range(41):
        for height in range(41):
            assert count_paths(width, height) == reference(width, height), (
                width,
                height,
            )


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a float.

    Computing the binomial with division rather than `math.comb` leaks a
    float, which is also wrong for large grids once precision runs out.
    """
    assert type(count_paths(3, 7)) is int
    assert type(count_paths(1, 1)) is int


def test_handles_a_large_grid_exactly() -> None:
    """Returns an exact count for a grid whose answer is enormous.

    A 60x60 grid has about 10^34 paths. Python integers are exact, so this is
    a real check: a float-based closed form loses precision here and a
    solution that caps or approximates fails outright.
    """
    assert count_paths(60, 60) == comb(118, 59)
    assert count_paths(100, 2) == 100


def test_handles_a_long_thin_grid() -> None:
    """Handles a grid that is very wide and only a few rows tall.

    This is where keeping the *shorter* dimension as the stored row matters:
    storing the long one is a hundred thousand entries for no reason.
    """
    assert count_paths(100_000, 1) == 1
    assert count_paths(100_000, 2) == 100_000
    assert count_paths(2, 100_000) == 100_000
