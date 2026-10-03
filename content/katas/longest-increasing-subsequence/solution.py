"""Reference solution. CI asserts this passes every test in `tests.py`."""

import bisect


def longest_increasing(numbers: list[int]) -> int:
    """Return the length of the longest strictly increasing subsequence.

    Patience sorting. `tails[k]` holds the smallest value that can end an
    increasing subsequence of length k + 1, and that list is always sorted -- so
    each new value is placed with a binary search: it either extends the longest
    run found so far, or it replaces the first tail it is not larger than.

    Why replacing helps rather than losing information: a shorter run ending in a
    smaller value is strictly more useful than one ending in a larger value,
    because anything that could extend the larger one can extend the smaller one
    too. So the replacement never shortens any future answer, and `len(tails)` is
    the answer at the end.

    `bisect_left`, not `bisect_right`, is where "strictly increasing" lives. With
    `bisect_right`, an equal value appends instead of replacing and `[7, 7, 7]`
    comes back as 3. Changing that one call is exactly the difference between
    this and the non-decreasing variant, which is worth knowing because it is the
    kind of specification detail that is easy to read past.

    Note what `tails` is NOT: an increasing subsequence of the input. It is a
    record of best-known endings, and reading it back as the answer gives
    nonsense. Recovering the actual subsequence needs predecessor links -- see
    the notes.
    """
    tails: list[int] = []
    for value in numbers:
        position = bisect.bisect_left(tails, value)
        if position == len(tails):
            tails.append(value)
        else:
            tails[position] = value
    return len(tails)
