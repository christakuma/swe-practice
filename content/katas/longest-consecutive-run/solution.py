"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_run(numbers: list[int]) -> int:
    """Return the length of the longest run of consecutive integers present.

    A set turns "is x + 1 present?" into a constant-time question, which means
    a run can be walked upward from any of its members. Building the set also
    collapses duplicates, so `[5, 5, 5]` is a run of one with no special case.

    Walking up from *every* value would be quadratic -- on a single run of n
    values, each member walks the rest of it. The fix is the whole kata:

        **A run has exactly one value that can start it -- the one whose
        predecessor is absent.**

    Check for that before walking, and each run is walked exactly once.

    This is why the nested loop is still O(n), which is worth being able to
    argue rather than assert. The outer loop runs once per distinct value. The
    inner loop only runs for run-starts, and across *all* run-starts its total
    work is the sum of the run lengths -- which is at most the number of
    distinct values. So the two loops together do O(n) work, not O(n^2),
    despite being nested.

    That argument is the reason the `value - 1 not in present` guard is not an
    optimisation to be added later. Without it the complexity claim is simply
    false, and the time limit is what notices.

    Sorting is the other good answer: sort, then scan counting consecutive
    neighbours. O(n log n) time, O(1) extra space if you may mutate the input.
    It is shorter and clearer, and it is banned here because the linear
    solution rests on a different idea -- *recognising* a run's start rather
    than *arranging* for runs to be adjacent.
    """
    present = set(numbers)
    best = 0
    for value in present:
        if value - 1 in present:
            continue  # not the start of a run; it will be counted from below
        length = 1
        while value + length in present:
            length += 1
        best = max(best, length)
    return best
