"""Reference solution. CI asserts this passes every test in `tests.py`."""


def max_slice_sum(numbers: list[int]) -> int:
    """Return the largest sum of any non-empty slice of a circular list.

    One pass keeps the best and the worst slice ending at each position. The
    best slice that does not wrap is the ordinary answer. The best one that
    does is everything except a stretch in the middle, so it is the total
    minus the *worst* slice.

    The guard at the end is the whole difficulty. When every value is
    negative the worst slice is the entire list, and the total minus it is an
    empty slice worth 0 -- which looks like a win and is not a slice. A
    negative `best` means exactly that case, so the wrap is not offered.
    """
    total = 0
    best = worst = numbers[0]
    best_here = worst_here = 0
    for value in numbers:
        total += value
        best_here = max(best_here + value, value)
        worst_here = min(worst_here + value, value)
        best = max(best, best_here)
        worst = min(worst, worst_here)
    return best if best < 0 else max(best, total - worst)
