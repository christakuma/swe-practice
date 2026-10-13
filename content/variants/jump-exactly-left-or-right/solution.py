"""Reference solution. CI asserts this passes every test in `tests.py`."""


def can_reach_a_zero(jumps: list[int], start: int) -> bool:
    """Return whether some position holding 0 can be reached from `start`.

    The positions are the nodes of a graph and each has at most two edges
    out: one jump to the left and one to the right. The question is plain
    reachability, so any search answers it; this one keeps a stack and a
    record of where it has been.

    The record is what makes it terminate. Positions can point at each other
    -- 1 sends you to 3 and 3 sends you back -- and a walk that does not
    remember would go round for ever. It is also what makes it linear: each
    position is expanded once.

    The furthest-reach scan from the standard problem does not apply. It
    relied on the reachable positions forming one unbroken block, and exact
    jumps leave gaps.
    """
    seen = [False] * len(jumps)
    seen[start] = True
    pending = [start]
    while pending:
        position = pending.pop()
        if jumps[position] == 0:
            return True
        for landing in (position - jumps[position], position + jumps[position]):
            if 0 <= landing < len(jumps) and not seen[landing]:
                seen[landing] = True
                pending.append(landing)
    return False
