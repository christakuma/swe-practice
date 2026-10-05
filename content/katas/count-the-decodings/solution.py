"""Reference solution. CI asserts this passes every test in `tests.py`."""

# The alphabet is the specification: A is 1 and Z is 26, so a two-digit
# reading is valid exactly in 10..26 -- 10 because a leading zero is not an
# encoding, 26 because there is no twenty-seventh letter.
SMALLEST_PAIR = 10
LARGEST_LETTER = 26


def count_decodings(digits: str) -> int:
    """Count the ways to decode a digit string into letters A=1..Z=26.

    The decodings of a prefix either take its last digit alone or its last two
    digits together, so each count is the sum of the one or two counts behind
    it -- a Fibonacci-shaped recurrence with the terms gated by validity:

    - one digit is usable when it is not `"0"`;
    - two digits are usable when they read between 10 and 26.

    **The `"0"` rules are the whole exercise.** A zero can never stand alone,
    and the encoding has no leading zeros, so `"06"` is not `F`. Both fall out
    of the two gates above without any special-casing -- and when neither gate
    opens, the count becomes 0 and every later count is a sum of zeros, so an
    undecodable string reports 0 with no early return. The invalidity
    propagates arithmetically, which is tidier than detecting it.

    Two variables rather than a table: the recurrence reaches back two places,
    so that is all the history needed (the same collapse as in
    `climbing-stairs`).

    The seeds are the fiddly part and they are not symmetric in meaning.
    `previous` is the count for the empty prefix and is **1** -- there is
    exactly one way to decode nothing, which is what lets a valid first digit
    inherit a count of 1. `before` is also 1 purely so that a valid two-digit
    opening like `"12"` can reach past the empty prefix and count the "both
    digits together" reading once. Seeding either at 0 silently halves the
    answer for inputs beginning with a two-digit letter.

    The empty string returns 0 rather than `previous`, because "one way to
    decode nothing" is bookkeeping for the recurrence, not an answer the
    problem accepts -- the prompt says the empty string has zero decodings.
    """
    if not digits:
        return 0

    before, previous = 1, 1
    for index, digit in enumerate(digits):
        current = 0
        if digit != "0":
            current += previous
        pair = int(digits[index - 1 : index + 1]) if index > 0 else 0
        if SMALLEST_PAIR <= pair <= LARGEST_LETTER:
            current += before
        before, previous = previous, current

    return previous
