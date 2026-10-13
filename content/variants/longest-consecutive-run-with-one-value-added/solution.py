"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_run(numbers: list[int]) -> int:
    """Return the longest consecutive run obtainable by adding one integer.

    The standard solution finds each run by walking up from its lowest value
    -- a value whose predecessor is absent -- so that every value is stepped
    over once. This keeps that walk and adds a second.

    When the first walk stops, `end + 1` is known to be absent: that is what
    stopped it. Suppose it is the value added. Then the run continues through
    it into whatever starts at `end + 2`, so a second walk from there measures
    how much further it reaches. If nothing is at `end + 2` the second walk
    covers nothing and the result is the run plus one, which is the "extend
    at the top" case with no code of its own.

    Extending at the *bottom* needs no code either. It gives the run plus
    one, the same as extending at the top, and joining a run to the one
    *below* it is found when that lower run is the one being walked.

    Each run is walked once as the first run and at most once as the second,
    so the whole thing is still linear.
    """
    present = set(numbers)
    best = 1
    for value in present:
        if value - 1 in present:
            continue
        end = value
        while end + 1 in present:
            end += 1
        beyond = end + 2
        while beyond in present:
            beyond += 1
        best = max(best, beyond - value)
    return best
