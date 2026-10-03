"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import flood_fill


def test_recolours_a_connected_region() -> None:
    """Paints the region containing the starting pixel."""
    image = [
        [1, 1, 1],
        [1, 1, 0],
        [1, 0, 1],
    ]

    assert flood_fill(image, 1, 1, 2) == [
        [2, 2, 2],
        [2, 2, 0],
        [2, 0, 1],
    ]


def test_leaves_a_separate_region_of_the_same_colour_alone() -> None:
    """Does not paint a same-coloured region that is not connected.

    The bottom-right 1 is the same colour as the region being painted and is
    reachable only diagonally. A solution that repaints every pixel of the
    original colour, rather than walking from the start, changes it.
    """
    image = [
        [1, 0],
        [0, 1],
    ]

    assert flood_fill(image, 0, 0, 2) == [[2, 0], [0, 1]]


def test_returns_immediately_when_the_colour_is_unchanged() -> None:
    """Terminates when the new colour is the colour already there.

    The input that hangs a solution without the early return: painting is the
    visited marker, so painting a pixel its own colour marks nothing and the
    walk revisits the same neighbours for ever.
    """
    image = [[1, 1], [1, 1]]

    assert flood_fill(image, 0, 0, 1) == [[1, 1], [1, 1]]


def test_handles_a_single_pixel_region() -> None:
    """Paints one pixel when nothing adjacent matches."""
    image = [
        [0, 1, 0],
        [1, 2, 1],
        [0, 1, 0],
    ]

    assert flood_fill(image, 1, 1, 9) == [
        [0, 1, 0],
        [1, 9, 1],
        [0, 1, 0],
    ]


def test_paints_the_whole_image_when_it_is_one_region() -> None:
    """Paints everything when the image is a single colour."""
    assert flood_fill([[5, 5], [5, 5]], 1, 0, 7) == [[7, 7], [7, 7]]


def test_follows_a_region_around_a_corner() -> None:
    """Follows a region that bends."""
    image = [
        [3, 3, 3],
        [0, 0, 3],
        [3, 3, 3],
    ]

    assert flood_fill(image, 0, 0, 1) == [
        [1, 1, 1],
        [0, 0, 1],
        [1, 1, 1],
    ]


def test_modifies_the_image_in_place() -> None:
    """Recolours the caller's image rather than a copy."""
    image = [[4]]

    assert flood_fill(image, 0, 0, 6) is image
    assert image == [[6]]


def test_handles_an_empty_image() -> None:
    """Returns an empty image unchanged."""
    assert flood_fill([], 0, 0, 1) == []


def test_fills_a_large_region_quickly() -> None:
    """Fills a region far larger than Python will recurse over.

    A 300x300 single-colour image: ninety thousand connected pixels. A
    recursive fill hits the 1000-frame limit about one percent of the way in.
    """
    size = 300
    image = [[0] * size for _ in range(size)]

    filled = flood_fill(image, 0, 0, 1)

    assert all(value == 1 for row in filled for value in row)
