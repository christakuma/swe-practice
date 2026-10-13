"""Reference solution. CI asserts this passes every test in `tests.py`."""


def anagram_positions(text: str, pattern: str) -> list[int]:
    """Return every index at which an anagram of `pattern` starts in `text`.

    `balance[c]` is how many more of `c` the window holds than the pattern
    needs, and `unsettled` counts the characters whose balance is not zero.
    The window is an anagram exactly when nothing is unsettled, so each step
    is two dict updates and one integer comparison, whatever the alphabet.
    """
    balance: dict[str, int] = {}
    unsettled = 0

    def shift(character: str, change: int) -> None:
        nonlocal unsettled
        before = balance.get(character, 0)
        after = before + change
        if before == 0:
            unsettled += 1
        elif after == 0:
            unsettled -= 1
        balance[character] = after

    for character in pattern:
        shift(character, -1)

    width = len(pattern)
    found = []
    for end, character in enumerate(text):
        shift(character, 1)
        if end >= width:
            shift(text[end - width], -1)
        if end >= width - 1 and unsettled == 0:
            found.append(end - width + 1)
    return found
