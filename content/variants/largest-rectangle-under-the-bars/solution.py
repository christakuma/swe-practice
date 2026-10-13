"""Reference solution. CI asserts this passes every test in `tests.py`."""


def largest_rectangle(heights: list[int]) -> int:
    """Return the area of the largest rectangle that fits under the bars.

    Every candidate rectangle is as tall as its shortest bar, so it is enough
    to consider, for each bar, the widest rectangle of exactly that height:
    it runs from just after the nearest shorter bar on the left to just
    before the nearest shorter bar on the right.

    `rising` is a stack of positions whose heights never decrease. When a bar
    arrives that is shorter than the one on top, the top's rectangle cannot
    extend any further right, so it is popped and measured. Its left limit is
    whatever is now on top of the stack -- the nearest bar to its left that
    is shorter -- or the start of the list if the stack is empty.

    A final bar of height 0 is shorter than everything and flushes the stack,
    so nothing is left unmeasured. Each position is pushed and popped once.
    """
    best = 0
    rising: list[int] = []
    for position, height in enumerate([*heights, 0]):
        while rising and heights[rising[-1]] > height:
            tall = heights[rising.pop()]
            left = rising[-1] + 1 if rising else 0
            best = max(best, tall * (position - left))
        rising.append(position)
    return best
