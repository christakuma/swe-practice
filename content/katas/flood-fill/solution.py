"""Reference solution. CI asserts this passes every test in `tests.py`."""


def flood_fill(
    image: list[list[int]], row: int, column: int, colour: int
) -> list[list[int]]:
    """Recolour the connected region containing one pixel.

    The guard that is the whole kata: **return early when the new colour is the
    colour already there.** Without it, repainting a region in its own colour
    never changes anything, so no pixel is ever marked as visited, and the walk
    goes round for ever between two neighbours. It is an infinite loop on an
    input that looks like a no-op, which is exactly the kind of input nobody
    thinks to try.

    With that out of the way, the region is a connected component and the walk is
    the one from count-islands -- except that the painting itself is the visited
    marker, which it can be only because the original colour has been captured
    first.

    Iterative, because a photograph-sized region is a hundred thousand pixels and
    a recursive fill is a hundred thousand frames.
    """
    if not image or not image[0]:
        return image

    original = image[row][column]
    if original == colour:
        return image

    rows, columns = len(image), len(image[0])
    stack = [(row, column)]
    image[row][column] = colour

    while stack:
        this_row, this_column = stack.pop()
        for next_row, next_column in (
            (this_row - 1, this_column),
            (this_row + 1, this_column),
            (this_row, this_column - 1),
            (this_row, this_column + 1),
        ):
            if (
                0 <= next_row < rows
                and 0 <= next_column < columns
                and image[next_row][next_column] == original
            ):
                image[next_row][next_column] = colour
                stack.append((next_row, next_column))
    return image
