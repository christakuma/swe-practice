"""Reference solution. CI asserts this passes every test in `tests.py`."""


def first_missing_positive(numbers: list[int]) -> int:
    """Return the smallest positive integer that is not in `numbers`.

    The answer lies in `1..n + 1`, so only the values `1..n` can affect it,
    and the list has exactly one position for each: value `v` lives at index
    `v - 1`. The first loop sends every such value home by swapping; the
    second reads off the first position whose resident is missing.

    The inner `while` matters -- a swap brings a new value to this position,
    and that one may need sending home too. It stops when the value here is
    out of range, or when its home already holds a copy of it. That second
    test is what handles duplicates, and it also covers a value that is
    already at home, since then the two positions are the same.

    Every swap puts one more value in its final place, so there are at most
    `n` swaps in total however the loops are nested.
    """
    size = len(numbers)
    for position in range(size):
        while True:
            value = numbers[position]
            if not 1 <= value <= size or numbers[value - 1] == value:
                break
            numbers[position], numbers[value - 1] = numbers[value - 1], value

    for position, value in enumerate(numbers):
        if value != position + 1:
            return position + 1
    return size + 1
