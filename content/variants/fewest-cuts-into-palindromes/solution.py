"""Reference solution. CI asserts this passes every test in `tests.py`."""


def fewest_cuts(text: str) -> int:
    """Return the fewest cuts that split `text` into palindromes.

    `cuts[i]` is the fewest cuts for the first `i` characters, and `cuts[0]`
    is -1 so that a palindrome reaching back to the start costs
    `cuts[0] + 1 = 0`. Everything else starts at the worst case, a cut after
    every character.

    The palindromes come from expanding around each centre, exactly as when
    counting them -- but each one found is *used*: a palindrome covering
    `low..high` says the first `high + 1` characters can be had for one cut
    more than the first `low`.

    The order is what makes that safe. `cuts[low]` is final once every
    palindrome ending before `low` has been seen, and those all have centres
    to the left of this one, which the loop has already finished.
    """
    size = len(text)
    cuts = list(range(-1, size))
    for centre in range(size):
        for width in (0, 1):
            low, high = centre, centre + width
            while low >= 0 and high < size and text[low] == text[high]:
                cuts[high + 1] = min(cuts[high + 1], cuts[low] + 1)
                low -= 1
                high += 1
    return max(cuts[size], 0)
