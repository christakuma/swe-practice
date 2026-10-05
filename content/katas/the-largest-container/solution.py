"""Reference solution. CI asserts this passes every test in `tests.py`."""


def largest_container(heights: list[int]) -> int:
    """Return the largest area formed by any two of the lines.

    Start at the widest container there is -- first line and last -- and walk
    inward. Every move costs width, so the only decision is which end to give
    up, and that decision has a proof rather than a heuristic behind it:

        Moving the taller line cannot help. The height of any container is
        capped by the shorter of its two lines, so keeping the shorter one
        means the height cannot rise, while the width has just fallen. Every
        such container is strictly worse than the one just measured.

    Therefore moving the *shorter* line is the only move that can improve
    anything -- and, more importantly, discarding it is safe. The best
    container involving that line is the one against the furthest line
    available, which is exactly the pair just measured. Nothing is lost.

    That is what makes this O(n) rather than a greedy guess that happens to
    work: each step eliminates a whole family of pairs with an argument, not a
    hope. The pointers meet after n steps and every pair that was never
    evaluated has been proven not to win.

    On equal heights either move is correct, for the same reason applied twice:
    whichever line is kept, the pair being abandoned was already measured at
    its widest.

    `best` starts at 0, so fewer than two lines needs no branch -- the loop
    does not run and 0 is already the answer.
    """
    low, high = 0, len(heights) - 1
    best = 0
    while low < high:
        area = min(heights[low], heights[high]) * (high - low)
        best = max(best, area)
        if heights[low] < heights[high]:
            low += 1
        else:
            high -= 1
    return best
