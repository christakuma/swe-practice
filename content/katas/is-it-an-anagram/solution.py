"""Reference solution. CI asserts this passes every test in `tests.py`."""


def is_anagram(first: str, second: str) -> bool:
    """Return whether `second` is a rearrangement of `first`.

    "Anagram" is a claim about **multiplicities**: each character occurs the
    same number of times in both. So the answer is a tally comparison, and the
    only real decision is how to compare two tallies.

    One dict suffices rather than two. Counting up for the first string and
    down for the second means a match leaves every entry at zero -- so the
    verdict is "did anything fail to cancel", which needs no second pass over a
    second structure.

    **The length check is load-bearing, not an optimisation.** The count-down
    loop can only detect a character that occurs *too often* in `second`; it
    never looks at what is left over in the tally. So without the length check,
    `"ab"` against `"a"` decrements the one `a`, finds nothing wrong, and
    returns True with a `b` still outstanding. Every proper prefix of an
    anagram passes.

    Equal lengths close that gap exactly: if the totals match and nothing in
    `second` ran out of budget, nothing can be left over. The cheap O(1) guard
    is what licenses the single tally -- the alternative is a second pass
    checking every count is zero.

    `collections.Counter(first) == Counter(second)` is the idiomatic Python and
    is what to ship. The loop is written out because the point of the kata is
    knowing what that comparison costs -- O(n) time and O(k) space for k
    distinct characters -- rather than treating it as free.
    """
    if len(first) != len(second):
        return False

    counts: dict[str, int] = {}
    for character in first:
        counts[character] = counts.get(character, 0) + 1
    for character in second:
        remaining = counts.get(character, 0)
        if remaining == 0:
            return False
        counts[character] = remaining - 1
    return True
