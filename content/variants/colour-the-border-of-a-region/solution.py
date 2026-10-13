"""Reference solution. CI asserts this passes every test in `tests.py`."""


def flood_fill(
    image: list[list[int]], row: int, column: int, colour: int
) -> list[list[int]]:
    """Recolour the border of the region containing a pixel, and return the image.

    Three steps kept strictly apart: collect the region, pick out its border,
    paint. Nothing is written until the third, so every question the first
    two ask -- is this neighbour the original colour? is it in the region? --
    is asked of an image that has not changed.

    Membership is a set of coordinates, not a colour. That is what lets the
    new colour equal the old one without the walk going round for ever, and
    what keeps a painted border pixel recognisable as part of the region.
    """
    if not image:
        return image
    rows, columns = len(image), len(image[0])
    original = image[row][column]

    region = {(row, column)}
    stack = [(row, column)]
    while stack:
        r, c = stack.pop()
        for cell in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            inside = 0 <= cell[0] < rows and 0 <= cell[1] < columns
            if inside and cell not in region and image[cell[0]][cell[1]] == original:
                region.add(cell)
                stack.append(cell)

    border = [
        (r, c)
        for r, c in region
        if not {(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)} <= region
    ]
    for r, c in border:
        image[r][c] = colour
    return image
