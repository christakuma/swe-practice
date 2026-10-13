"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_slices(numbers: list[int], limit: int) -> int:
    """Count the contiguous slices whose product is strictly below `limit`.

    Positive values make the product grow with the window, so a window can
    slide: extend it on the right, and while the product is too large divide
    out values from the left. The division is exact because every value in
    the product is a factor of it.

    Once the window ending at `end` is valid, so is every suffix of it, which
    is `end - start + 1` slices. A limit of 0 or 1 admits nothing -- every
    product is at least 1 -- and is returned early, because the shrinking
    loop would otherwise run off the end of an empty window.
    """
    if limit <= 1:
        return 0
    count = 0
    product = 1
    start = 0
    for end, value in enumerate(numbers):
        product *= value
        while product >= limit:
            product //= numbers[start]
            start += 1
        count += end - start + 1
    return count
