"""Reference solution. CI asserts this passes every test in `tests.py`."""


def max_slice_sum(numbers: list[int]) -> int:
    """Return the largest sum of a slice with at most one element left out.

    Kadane's scan with a second running value. `whole` is the best sum of a
    slice ending at the current element with nothing dropped -- the usual
    one. `dropped` is the best sum of a slice ending here from which one
    element has already been removed.

    `dropped` has two sources: the earlier drop carried forward and extended
    by this element, or this element being the one dropped, which leaves
    exactly the previous `whole`. It is updated first, while `whole` still
    describes the previous position.

    `dropped` starts at minus infinity, meaning "not possible yet": before the
    second element nothing can have been dropped from a non-empty slice.
    """
    whole = best = numbers[0]
    dropped = float("-inf")
    for value in numbers[1:]:
        dropped = max(dropped + value, whole)
        whole = max(whole + value, value)
        best = max(best, whole, dropped)
    return int(best)
