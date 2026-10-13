"""Reference solution. CI asserts this passes every test in `tests.py`."""


def move_zeroes(numbers: list[int]) -> None:
    """Move every zero to the front of the list, in place.

    The mirror image of packing to the front. Reading from the back and
    writing from the back keeps the non-zero values in their original order,
    and the read index is never behind the write index, so nothing is
    overwritten before it has been read. The positions left over at the front
    are then filled with zeros.
    """
    write = len(numbers) - 1
    for read in range(len(numbers) - 1, -1, -1):
        if numbers[read] != 0:
            numbers[write] = numbers[read]
            write -= 1
    for index in range(write + 1):
        numbers[index] = 0
