"""Reference solution. CI asserts this passes every test in `tests.py`."""

from bisect import bisect_right


def longest_non_decreasing(numbers: list[int]) -> int:
    """Return the length of the longest non-decreasing subsequence.

    `tails[k]` is the smallest value any non-decreasing subsequence of length
    `k + 1` can end with. A new value extends the longest subsequence whose
    tail is at most that value, so it replaces the first tail *strictly
    greater* than it -- `bisect_right`. The strictly increasing version uses
    `bisect_left`, and that one word is the entire difference.
    """
    tails: list[int] = []
    for value in numbers:
        position = bisect_right(tails, value)
        if position == len(tails):
            tails.append(value)
        else:
            tails[position] = value
    return len(tails)
