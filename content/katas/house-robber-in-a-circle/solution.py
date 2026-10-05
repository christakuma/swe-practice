"""Reference solution. CI asserts this passes every test in `tests.py`."""


def _straight_line(houses: list[int]) -> int:
    """`house-robber` on a straight row: the most takeable with no two adjacent.

    Two rolling values. `taken` is the best total for the row so far *ending
    with this house used*; `skipped` is the best *without* it. Each house is
    either taken -- adding to the best that excluded its predecessor -- or
    skipped, keeping the better of the two.
    """
    taken = skipped = 0
    for amount in houses:
        taken, skipped = skipped + amount, max(skipped, taken)
    return max(taken, skipped)


def best_haul(houses: list[int]) -> int:
    """Return the largest total takeable from houses in a circle.

    The circle adds **exactly one** rule to the straight-line problem: the
    first and last houses cannot both be taken. So rather than inventing a new
    recurrence that tracks whether the first house was used -- which is where
    this problem usually goes wrong -- split on that single constraint:

        any valid answer either omits the first house or omits the last.

    Those two cases are exhaustive (an answer taking both is invalid) and each
    one is a plain straight line, which is already solved. Two calls, take the
    better.

    **That is the move worth taking away: when a problem is a solved problem
    plus one constraint, case-split on the constraint rather than extending the
    recurrence.** The split costs a constant factor -- two linear passes
    instead of one -- and it reuses a function you already trust instead of a
    new one you do not.

    The two cases overlap, incidentally. An answer omitting both the first and
    last houses is counted twice, which is harmless: `max` does not care about
    double-counting, only about missing something. Worth noticing because
    "exhaustive but overlapping" is fine for a maximum and fatal for a count --
    the same split would be wrong in `count-the-decodings`.

    A single house is the one input where both slices are empty, so it would
    report 0. It is handled before the split, which is cheaper than making the
    slices clever.
    """
    if not houses:
        return 0
    if len(houses) == 1:
        return houses[0]
    return max(_straight_line(houses[1:]), _straight_line(houses[:-1]))
