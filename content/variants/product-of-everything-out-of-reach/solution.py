"""Reference solution. CI asserts this passes every test in `tests.py`."""


def product_except_window(numbers: list[int], k: int) -> list[int]:
    """Return, for each position, the product of everything out of its reach.

    `before[i]` is the product of the first `i` values and `after[i]` the
    product of everything from `i` on, each with a 1 for the empty case. What
    position `i` wants is everything left of `i - k` and everything right of
    `i + k`, so the two are read at those positions, clamped to the list.
    """
    size = len(numbers)
    before = [1] * (size + 1)
    for index, value in enumerate(numbers):
        before[index + 1] = before[index] * value
    after = [1] * (size + 1)
    for index in range(size - 1, -1, -1):
        after[index] = after[index + 1] * numbers[index]
    return [
        before[max(index - k, 0)] * after[min(index + k + 1, size)]
        for index in range(size)
    ]
