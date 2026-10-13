"""Reference solution. CI asserts this passes every test in `tests.py`."""


def closest_sum(numbers: list[int], target: int) -> int:
    """Return the sum of three values that is closest to `target`.

    A sorted copy, one value fixed, and two pointers closing in on the rest.
    A sum below the target can only be improved by raising it, so the left
    pointer moves; above, the right one does. Every candidate the pointers
    pass is compared with the best so far.

    Candidates are ranked by `(distance, sum)`, which is the tie rule: at the
    same distance, the smaller sum wins.
    """
    ordered = sorted(numbers)
    best = ordered[0] + ordered[1] + ordered[2]
    for first in range(len(ordered) - 2):
        low, high = first + 1, len(ordered) - 1
        while low < high:
            total = ordered[first] + ordered[low] + ordered[high]
            if (abs(total - target), total) < (abs(best - target), best):
                best = total
            if total == target:
                return total
            if total < target:
                low += 1
            else:
                high -= 1
    return best
