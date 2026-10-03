"""Reference solution. CI asserts this passes every test in `tests.py`."""


def ways_to_climb(steps: int) -> int:
    """Count the distinct ways to climb `steps` steps, one or two at a time.

    The recurrence comes from asking what the *last* step was. It was either a
    single step, from `steps - 1`, or a double, from `steps - 2`, and those two
    sets of routes are disjoint and cover everything -- so
    `ways(n) = ways(n - 1) + ways(n - 2)`. Fibonacci, arrived at rather than
    recognised.

    `ways(0) = 1` is the base case that looks wrong and is load-bearing. There is
    one way to climb no steps: take none. Setting it to 0 makes every answer 0,
    and `ways(2)` is the shortest input that shows it -- 1+1 and 2 are two ways,
    and one of them is "arrive from step 0".

    Two variables rather than a table, because the recurrence only ever reaches
    back two places. That is the whole of what people mean by "space-optimised
    DP": keep the window the recurrence actually reads.

    The naive recursion is exponential -- 2^n calls, recomputing ways(n-2) twice
    at every level -- which is the canonical demonstration of why memoising
    matters, and why the bottom-up loop needs neither a cache nor a stack.
    """
    previous, current = 1, 1
    for _ in range(steps):
        previous, current = current, previous + current
    return previous
