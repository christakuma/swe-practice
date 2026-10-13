"""Reference solution. CI asserts this passes every test in `tests.py`."""


def flood_fill(
    image: list[list[int]], row: int, column: int, colour: int
) -> list[list[int]]:
    """Recolour the region containing one pixel, with diagonals connected.

    The standard flood with eight neighbours instead of four. A pixel is
    painted when it is pushed, which is what stops it being pushed twice, and
    a region already of the new colour is left alone -- otherwise painted
    pixels would still look unvisited and the search would never end.
    """
    if not image:
        return image
    original = image[row][column]
    if original == colour:
        return image
    image[row][column] = colour
    stack = [(row, column)]
    while stack:
        y, x = stack.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if (
                    0 <= ny < len(image)
                    and 0 <= nx < len(image[ny])
                    and image[ny][nx] == original
                ):
                    image[ny][nx] = colour
                    stack.append((ny, nx))
    return image
