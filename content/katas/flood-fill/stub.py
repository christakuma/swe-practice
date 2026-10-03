"""Your solution goes here. The tests import `flood_fill` from here."""


def flood_fill(
    image: list[list[int]], row: int, column: int, colour: int
) -> list[list[int]]:
    """Recolour the connected region containing one pixel.

    Two pixels are in the same region when they touch up, down, left or right
    and started with the same colour. Diagonals do not connect.

    Args:
        image: a rectangular grid of colour numbers. Modified in place.
        row: the starting pixel's row.
        column: the starting pixel's column.
        colour: the colour to paint the region.

    Returns:
        The same image object, recoloured.
    """
    raise NotImplementedError
