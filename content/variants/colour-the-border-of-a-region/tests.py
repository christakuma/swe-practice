"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import flood_fill

type Image = list[list[int]]


def by_definition(image: Image, row: int, column: int, colour: int) -> Image:
    """Build the answer from the definition, growing the region until it stops."""
    rows, columns = len(image), len(image[0])
    original = image[row][column]
    region = {(row, column)}
    grew = True
    while grew:
        grew = False
        for r, c in product(range(rows), range(columns)):
            if (r, c) in region or image[r][c] != original:
                continue
            if {(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)} & region:
                region.add((r, c))
                grew = True
    result = [list(line) for line in image]
    for r, c in region:
        on_edge = r in (0, rows - 1) or c in (0, columns - 1)
        around = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        if on_edge or any(cell not in region for cell in around):
            result[r][c] = colour
    return result


def test_leaves_the_interior_alone() -> None:
    """Keeps the colour of pixels whose four neighbours are all in the region."""
    image = [[1] * 4 for _ in range(4)]

    assert flood_fill(image, 1, 1, 7) == [
        [7, 7, 7, 7],
        [7, 1, 1, 7],
        [7, 1, 1, 7],
        [7, 7, 7, 7],
    ]


def test_a_neighbour_of_another_colour_makes_a_border() -> None:
    """Recolours region pixels that touch a pixel outside the region."""
    image = [
        [0, 0, 0, 0, 0],
        [0, 5, 5, 5, 0],
        [0, 5, 5, 5, 0],
        [0, 5, 5, 5, 0],
        [0, 0, 0, 0, 0],
    ]

    assert flood_fill(image, 2, 2, 8) == [
        [0, 0, 0, 0, 0],
        [0, 8, 8, 8, 0],
        [0, 8, 5, 8, 0],
        [0, 8, 8, 8, 0],
        [0, 0, 0, 0, 0],
    ]


def test_the_edge_of_the_image_makes_a_border() -> None:
    """Recolours region pixels on the first and last rows and columns."""
    image = [
        [1, 1, 1],
        [1, 1, 1],
        [1, 1, 1],
    ]

    assert flood_fill(image, 0, 0, 2) == [
        [2, 2, 2],
        [2, 1, 2],
        [2, 2, 2],
    ]


def test_a_thin_region_is_all_border() -> None:
    """Recolours every pixel of a region with no interior."""
    image = [
        [1, 1, 2],
        [1, 2, 2],
    ]

    assert flood_fill(image, 0, 0, 9) == [[9, 9, 2], [9, 2, 2]]
    assert flood_fill([[4]], 0, 0, 6) == [[6]]


def test_a_hole_in_the_region_has_a_border_too() -> None:
    """Recolours the pixels around a hole in the middle of the region."""
    image = [[1] * 5 for _ in range(5)]
    image[2][2] = 3

    assert flood_fill(image, 0, 0, 7) == [
        [7, 7, 7, 7, 7],
        [7, 1, 7, 1, 7],
        [7, 7, 3, 7, 7],
        [7, 1, 7, 1, 7],
        [7, 7, 7, 7, 7],
    ]


def test_does_not_cross_diagonals() -> None:
    """Leaves alone a same-coloured pixel that touches only at a corner."""
    image = [
        [1, 2],
        [2, 1],
    ]

    assert flood_fill(image, 0, 0, 5) == [[5, 2], [2, 1]]


def test_does_not_touch_other_regions_of_the_same_colour() -> None:
    """Leaves alone a separate region that has the starting pixel's colour."""
    image = [[1, 1, 0, 1, 1]]

    assert flood_fill(image, 0, 0, 3) == [[3, 3, 0, 1, 1]]


def test_painting_with_the_colour_already_there() -> None:
    """Terminates and changes nothing when the new colour is the old one."""
    image = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]

    assert flood_fill(image, 1, 1, 1) == [[1, 1, 1], [1, 1, 1], [1, 1, 1]]


def test_painting_with_a_colour_used_elsewhere() -> None:
    """Judges the border by the original colours when the new colour is a neighbour's.

    Painting the border with 2 beside a region of 2s must not let the fill
    leak into them, or make the painted pixels look like outsiders.
    """
    image = [
        [1, 1, 1, 2],
        [1, 1, 1, 2],
        [1, 1, 1, 2],
    ]

    assert flood_fill(image, 1, 1, 2) == [
        [2, 2, 2, 2],
        [2, 1, 2, 2],
        [2, 2, 2, 2],
    ]


def test_returns_the_same_image_object() -> None:
    """Modifies the image in place and returns that same object."""
    image = [[1, 1], [1, 1]]
    first_row = image[0]

    result = flood_fill(image, 0, 0, 4)

    assert result is image
    assert result[0] is first_row


def test_an_empty_image_is_returned_as_it_is() -> None:
    """Returns an empty image unchanged."""
    image: Image = []

    assert flood_fill(image, 0, 0, 1) is image


def test_agrees_with_the_definition_on_every_small_image() -> None:
    """Matches a from-the-definition answer for every small image.

    Every 3 x 3 image in two colours and a spread of 3 x 5 ones, from every
    starting pixel, painted with each of those colours and a third.
    """
    small = [(3, cells) for cells in product((0, 1), repeat=9)]
    wide = [(5, cells) for cells in list(product((0, 1), repeat=15))[::37]]
    for width, cells in small + wide:
        for row, column in product(range(3), range(width)):
            for colour in (0, 1, 2):
                image = [list(cells[r * width : (r + 1) * width]) for r in range(3)]
                expected = by_definition(image, row, column, colour)
                assert flood_fill(image, row, column, colour) == expected, (
                    cells,
                    row,
                    column,
                    colour,
                )


def test_handles_a_region_covering_a_large_image() -> None:
    """Handles a 300 x 300 region without recursing."""
    size = 300
    image = [[4] * size for _ in range(size)]

    flood_fill(image, 150, 150, 9)

    assert image[0] == [9] * size
    assert image[-1] == [9] * size
    assert image[150] == [9] + [4] * (size - 2) + [9]
    assert sum(line.count(9) for line in image) == 4 * size - 4
