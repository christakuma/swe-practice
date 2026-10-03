"""Reference solution. CI asserts this passes every test in `tests.py`."""


def can_reach_the_end(jumps: list[int]) -> bool:
    """Whether the last position is reachable from the first.

    One pass, one number: the furthest position reachable so far. Walk forward;
    if the current position is beyond that frontier, nothing can reach it and
    nothing beyond it, so the answer is no. Otherwise widen the frontier.

    This is the rare problem where greedy is not only correct but *obviously* so,
    once stated as a frontier rather than as a choice of jumps: the reachable set
    is always a prefix, because a jump of length n from position i can land
    anywhere up to i + n, including every position in between. There is no
    decision to make, so there is nothing to get wrong by being greedy -- and the
    dynamic-programming version with a reachable flag per position is O(n^2) for
    no benefit.

    The frontier is "furthest index", not "remaining fuel". Both work; the
    fuel version (decrement each step, refresh when the current jump is bigger)
    is the same algorithm and is harder to reason about at the boundaries, which
    is where this problem's wrong answers live.
    """
    furthest = 0
    for index, jump in enumerate(jumps):
        if index > furthest:
            return False
        furthest = max(furthest, index + jump)
    return True
