"""Reference solution. CI asserts this passes every test in `tests.py`."""


def fewest_removals(intervals: list[tuple[int, int]]) -> int:
    """Return the fewest intervals to remove so the rest do not overlap.

    **Flip the question.** Removing the fewest is keeping the most, and
    counting survivors is far easier to reason about than choosing deletions --
    there is no "which one of this overlapping pair should go?" to agonise over,
    only "can I take this next?".

    Then it is the classic interval-scheduling greedy, and the whole content is
    the sort key:

        sort by **end**, not by start.

    The argument: among the intervals you could take next, the one that finishes
    earliest leaves the most room for everything after it, and it never costs
    you anything -- any solution using a later-finishing interval can swap in
    the earlier-finishing one and remain valid. So the greedy choice is safe at
    every step, which is what makes a greedy algorithm *correct* rather than
    merely plausible.

    Sorting by start is the intuitive key and it is wrong. One long interval
    starting first blocks several short ones behind it, and a start-ordered
    scan takes the long one because it got there first. The classic
    counter-example is `[(1, 100), (2, 3), (3, 4)]`: by end you keep two, by
    start you keep one.

    `start >= last_end` and not `>`: touching does not count as overlapping, so
    `(1, 2)` and `(2, 3)` may both stay. This is the same endpoint convention as
    `insert-an-interval` and it goes the *other* way there -- touching intervals
    merge when you are combining them and coexist when you are packing them.
    Worth reading the prompt rather than carrying the comparison over.

    `kept` is never decremented and `last_end` only ever moves forward, so the
    scan is a single pass after the sort.
    """
    ordered = sorted(intervals, key=lambda interval: interval[1])
    kept = 0
    last_end = None
    for start, end in ordered:
        if last_end is None or start >= last_end:
            kept += 1
            last_end = end
    return len(intervals) - kept
