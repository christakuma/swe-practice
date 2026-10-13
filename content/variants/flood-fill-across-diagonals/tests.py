"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import flood_fill


def by_growing(
    image: list[list[int]], row: int, column: int, colour: int
) -> list[list[int]]:
    """Grow the region one ring at a time until it stops growing."""
    original = image[row][column]
    region = {(row, column)}
    while True:
        grown = {
            (y, x)
            for y in range(len(image))
            for x in range(len(image[y]))
            if image[y][x] == original
            and any(abs(y - a) <= 1 and abs(x - b) <= 1 for a, b in region)
        }
        if grown <= region:
            break
        region |= grown
    return [
        [colour if (y, x) in region else value for x, value in enumerate(line)]
        for y, line in enumerate(image)
    ]


def test_crosses_a_diagonal() -> None:
    """Paints a pixel that touches the region only at a corner."""
    image = [[1, 1, 1], [1, 1, 0], [1, 0, 1]]

    assert flood_fill(image, 1, 1, 2) == [[2, 2, 2], [2, 2, 0], [2, 0, 2]]


def test_follows_a_diagonal_line() -> None:
    """Follows a region made only of corner contacts."""
    assert flood_fill([[1, 0], [0, 1]], 0, 0, 5) == [[5, 0], [0, 5]]


def test_stops_at_a_gap() -> None:
    """Does not paint a same-coloured pixel that is not connected."""
    assert flood_fill([[1, 0, 1]], 0, 0, 7) == [[7, 0, 1]]


def test_terminates_when_the_colour_is_unchanged() -> None:
    """Returns when the region already has the new colour."""
    assert flood_fill([[3, 3], [3, 3]], 0, 0, 3) == [[3, 3], [3, 3]]


def test_works_in_place_and_handles_an_empty_image() -> None:
    """Returns the image it was given, including an empty one."""
    image = [[1, 1]]

    assert flood_fill(image, 0, 0, 2) is image
    assert flood_fill([], 0, 0, 1) == []


def test_agrees_with_growing_the_region() -> None:
    """Matches a grow-until-stable fill for every 3x3 image of two colours."""
    for cells in product((0, 1), repeat=9):
        for row, column in product(range(3), repeat=2):
            image = [list(cells[y * 3 : y * 3 + 3]) for y in range(3)]
            expected = by_growing(image, row, column, 2)
            assert flood_fill(image, row, column, 2) == expected, (cells, row, column)


def test_fills_a_large_region() -> None:
    """Fills ninety thousand pixels without recursing."""
    side = 300
    image = [[4] * side for _ in range(side)]

    flood_fill(image, 150, 150, 9)

    assert all(value == 9 for line in image for value in line)
