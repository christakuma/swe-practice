"""Reference solution. CI asserts this passes every test in `tests.py`."""

#: Z, the last letter there is a code for.
LAST_LETTER = 26


def decodings(digits: str) -> list[str]:
    """Return every decoding of a digit string into letters A=1..Z=26.

    A depth-first walk with at most two branches at each position: one digit
    or two. A leading zero ends a branch, which covers both rules at once --
    a lone 0 is not a letter and neither is 06. The empty string is answered
    before the walk starts, because the walk would otherwise record the one
    empty decoding of it.
    """
    if not digits:
        return []
    found: list[str] = []
    letters: list[str] = []

    def extend(at: int) -> None:
        if at == len(digits):
            found.append("".join(letters))
            return
        if digits[at] == "0":
            return
        for width in (1, 2):
            piece = digits[at : at + width]
            if len(piece) == width and int(piece) <= LAST_LETTER:
                letters.append(chr(64 + int(piece)))
                extend(at + width)
                letters.pop()

    extend(0)
    return sorted(found)
