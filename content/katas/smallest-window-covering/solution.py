"""Reference solution. CI asserts this passes every test in `tests.py`."""


def smallest_window(text: str, needed: str) -> str:
    """Return the shortest substring of `text` covering every character of
    `needed`, earliest on a tie.

    Grow the window on the right until it covers everything, shrink it from the
    left while it still covers, record it, and carry on. Each end moves forward
    at most n times, so the scan is linear -- the work is in making "does this
    window cover it?" answerable in O(1).

    **`outstanding` is that answer.** Comparing two tallies every step would be
    O(k) and would make the whole thing O(nk). Instead one integer tracks how
    many *required character slots* are still unfilled, and the window covers
    exactly when it reaches zero.

    Two details keep that integer honest, and they are the whole difficulty.

    `remaining` is allowed to go **negative**. A count below zero means the
    window holds more copies of that character than required -- and that is
    precisely the signal the shrink loop needs: a leftmost character whose
    count is negative is surplus and can be dropped without losing coverage.
    Clamping at zero throws away the only information that tells you which
    character is safe to discard.

    `outstanding` is decremented **only when the character was still needed**,
    which is when its remaining requirement is above zero. Drop that guard and
    a second `A` in a window needing one `A` satisfies the requirement twice,
    so `outstanding` reaches zero early and the window is reported as covering
    when it does not.

    `<` rather than `<=` when comparing widths gives "earliest on a tie", since
    windows are discovered left to right.

    The empty `needed` returns "" through the initial `outstanding` of zero
    never being beaten by a recorded window -- no branch required, and it
    matches the prompt: there is nothing to cover, so no window is the answer.
    """
    if not needed or not text:
        return ""

    remaining: dict[str, int] = {}
    for character in needed:
        remaining[character] = remaining.get(character, 0) + 1

    outstanding = len(needed)
    best_start, best_length = 0, 0
    left = 0

    for right, character in enumerate(text):
        if character in remaining:
            if remaining[character] > 0:
                outstanding -= 1
            remaining[character] -= 1

        while outstanding == 0:
            width = right - left + 1
            if best_length == 0 or width < best_length:
                best_start, best_length = left, width

            dropped = text[left]
            left += 1
            if dropped in remaining:
                remaining[dropped] += 1
                if remaining[dropped] > 0:
                    outstanding += 1

    return text[best_start : best_start + best_length]
