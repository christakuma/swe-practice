"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_run(numbers: list[int]) -> tuple[int, int] | None:
    """Return the first and last values of the longest run of consecutive
    integers present.

    A value starts a run only if the value below it is absent, so each run is
    walked once, from its start, and the whole scan is linear. Runs are
    compared by `(-length, start)`: longer first, and the lower start on a
    tie. The tie rule is in the key because a set is visited in no
    particular order.
    """
    present = set(numbers)
    best: tuple[int, int] | None = None
    for start in present:
        if start - 1 in present:
            continue
        end = start
        while end + 1 in present:
            end += 1
        if best is None or (start - end, start) < (best[0] - best[1], best[0]):
            best = (start, end)
    return best
