"""Reference solution. CI asserts this passes every test in `tests.py`."""


def best_haul(houses: list[int]) -> list[int]:
    """Return the positions of the houses to take from a circle.

    The reduction is the standard one: the first and last house cannot both
    be taken, so the best selection lies wholly in the line that omits the
    last house or wholly in the line that omits the first. Solve both lines
    and keep the better.

    What changes is the line solver. The total needs two variables; the
    selection needs the table, because the choice made at each house is only
    recoverable by comparing neighbouring entries afterwards.
    """
    count = len(houses)
    if count == 0:
        return []
    if count == 1:
        return [0]
    without_last = _best_line(houses, 0, count - 1)
    without_first = _best_line(houses, 1, count)
    return max(
        without_last, without_first, key=lambda picks: sum(houses[i] for i in picks)
    )


def _best_line(houses: list[int], start: int, stop: int) -> list[int]:
    """The best selection from the straight line `houses[start:stop]`.

    `best[i]` is the most that can be taken from the first `i` houses of the
    line. Reading it backwards: where `best[i] == best[i - 1]` the `i`th
    house added nothing and is skipped; otherwise it was taken, and the house
    before it could not have been, so the walk steps back two.

    The positions recorded are positions in `houses`, not in the line, which
    is what the `start +` is for.
    """
    length = stop - start
    best = [0] * (length + 1)
    for i in range(1, length + 1):
        take = houses[start + i - 1] + (best[i - 2] if i > 1 else 0)
        best[i] = max(best[i - 1], take)

    picks = []
    i = length
    while i >= 1:
        if best[i] == best[i - 1]:
            i -= 1
        else:
            picks.append(start + i - 1)
            i -= 2
    picks.reverse()
    return picks
