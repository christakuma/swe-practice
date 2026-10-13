"""Reference solution. CI asserts this passes every test in `tests.py`."""


def two_sum(numbers: list[int], target: int) -> tuple[int, int]:
    """Return the two 1-based positions whose values add up to `target`.

    Two indices from the ends. When the sum is too small the low value is
    finished -- it has already been tried with the largest value still in
    play -- so `low` moves up; when it is too big the high value is finished
    for the mirror-image reason. Each step retires one value, so the walk is
    linear and holds two integers.
    """
    low, high = 0, len(numbers) - 1
    while low < high:
        total = numbers[low] + numbers[high]
        if total == target:
            return (low + 1, high + 1)
        if total < target:
            low += 1
        else:
            high -= 1
    raise ValueError("no pair adds up to the target")
