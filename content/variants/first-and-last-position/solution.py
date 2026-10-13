"""Reference solution. CI asserts this passes every test in `tests.py`."""


def _first_at_least(numbers: list[int], value: int) -> int:
    """The first position holding something >= `value`, or len(numbers)."""
    low, high = 0, len(numbers)
    while low < high:
        middle = (low + high) // 2
        if numbers[middle] < value:
            low = middle + 1
        else:
            high = middle
    return low


def search(numbers: list[int], target: int) -> tuple[int, int]:
    """Return the first and last positions of `target` in a sorted list.

    Two boundary searches. The run of targets starts at the first position
    holding something at least `target` and ends just before the first
    position holding something at least `target + 1` -- for integers, the
    same thing as "greater than `target`".

    A boundary search never stops early. Meeting the target only tells it
    which side to keep, so a run of a million equal values costs the same
    twenty steps as a run of one.

    If the first boundary is off the end, or does not hold the target, the
    target is absent.
    """
    first = _first_at_least(numbers, target)
    if first == len(numbers) or numbers[first] != target:
        return (-1, -1)
    return (first, _first_at_least(numbers, target + 1) - 1)
