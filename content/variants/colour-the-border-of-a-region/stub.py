"""Your solution goes here. The tests import `flood_fill` from this module."""


def flood_fill(
    image: list[list[int]], row: int, column: int, colour: int
) -> list[list[int]]:
    """Recolour the border of the region containing a pixel, and return the image.

    Two pixels are in the same region when they touch up, down, left or right
    and started with the same colour. A region pixel is on the border when it
    is on the edge of the image or has a neighbour outside the region.

    Args:
        image: a rectangular grid of colour numbers. Modified in place.
        row: the starting pixel's row.
        column: the starting pixel's column.
        colour: the colour to paint the border.

    Returns:
        The same `image` object, with the border of the region recoloured.
    """
    raise NotImplementedError
