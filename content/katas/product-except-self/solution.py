"""Reference solution. CI asserts this passes every test in `tests.py`."""


def product_except_self(numbers: list[int]) -> list[int]:
    """Return, for each position, the product of every other element.

    Division is the answer everyone reaches for -- total product divided by this
    element -- and it is wrong for a reason worth internalising: a single zero
    makes the total product zero, so every answer becomes zero or a division by
    zero, and the correct answer at the zero's own position is the product of
    everything else. Two zeros make it worse. The constraint "no division" is not
    arbitrary; it is pointing at that.

    What is left is the observation that the answer at i is (everything to the
    left of i) times (everything to the right of i), and both of those are
    running products that can be accumulated in one pass each.

    The second pass multiplies into the same list rather than building another,
    which is the whole reason for the two-pass shape: the output array is not
    counted as extra space, so this is O(1) auxiliary.
    """
    size = len(numbers)
    result = [1] * size

    running = 1
    for index in range(size):
        result[index] = running
        running *= numbers[index]

    running = 1
    for index in reversed(range(size)):
        result[index] *= running
        running *= numbers[index]

    return result
