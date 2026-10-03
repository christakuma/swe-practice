"""Reference solution. CI asserts this passes every test in `tests.py`."""


def max_slice_sum(numbers: list[int]) -> int:
    """Return the largest sum of any non-empty contiguous slice.

    Kadane's algorithm, and the decision it makes at each element is the only
    thing to remember: either extend the slice that ends at the previous element,
    or start a new slice here. `max(value, best_here + value)` is that choice, and
    it is correct because a prefix with a negative sum can never help -- dropping
    it is always at least as good as keeping it.

    Initialising both running values to `numbers[0]` rather than to 0 is what
    makes an all-negative list work. Starting from 0 quietly encodes "the empty
    slice is allowed", so `[-3, -1, -2]` comes back as 0 -- an answer that is not
    any slice of the input. The specification says non-empty, and the
    initialisation is where that is enforced.

    Two running values, no array: `best_here` is the best slice ending at this
    element and `best_anywhere` is the best seen so far. That is the whole state,
    which is why this is O(1) space while the obvious prefix-sum approach is
    O(n).
    """
    best_here = best_anywhere = numbers[0]
    for value in numbers[1:]:
        best_here = max(value, best_here + value)
        best_anywhere = max(best_anywhere, best_here)
    return best_anywhere
