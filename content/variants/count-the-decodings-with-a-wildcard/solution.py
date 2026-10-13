"""Reference solution. CI asserts this passes every test in `tests.py`."""

STAR = "*"
ANY_DIGIT = 9  # a star is 1 to 9
TEENS_AND_TWENTIES = 15  # 11-19 and 21-26: the two-star letters


def _alone(character: str) -> int:
    """How many letters this one character can be."""
    if character == STAR:
        return ANY_DIGIT
    return 0 if character == "0" else 1


def _together(first: str, second: str) -> int:
    """How many letters these two characters can be, read as one number."""
    if first == STAR and second == STAR:
        return TEENS_AND_TWENTIES
    if first == STAR:
        # 1x is always a letter; 2x only up to 26.
        return 2 if second <= "6" else 1
    if second == STAR:
        if first == "1":
            return ANY_DIGIT
        return 6 if first == "2" else 0  # 21 to 26
    return 1 if "10" <= first + second <= "26" else 0


def count_decodings(digits: str) -> int:
    """Count the ways to decode a digit string that may contain wildcards.

    The standard recurrence with its two yes-or-no questions turned into
    counts. `ways(i)` is still built from `ways(i - 1)` and `ways(i - 2)`,
    but each is multiplied by *how many* letters the last character, or the
    last two, could be -- which is where every choice of digit for a star is
    counted, without any star ever being expanded.

    The four cases of `_together` are the whole difficulty. Star-star is
    fifteen: the numbers 11 to 26 with no zero in them.
    """
    if not digits:
        return 0
    before, last = 1, _alone(digits[0])
    for index in range(1, len(digits)):
        alone = _alone(digits[index]) * last
        together = _together(digits[index - 1], digits[index]) * before
        before, last = last, alone + together
    return last
