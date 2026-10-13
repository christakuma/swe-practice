"""Reference solution. CI asserts this passes every test in `tests.py`."""


def smallest_window(text: str) -> str:
    """Return the shortest substring holding every distinct character of `text`.

    The window is complete when it holds as many distinct characters as the
    text does. Each time it becomes complete it is shrunk from the left for
    as long as it stays so, and the shortest seen is kept; `<` rather than
    `<=` on the length keeps the earliest of equals.
    """
    needed = len(set(text))
    counts: dict[str, int] = {}
    best = ""
    start = 0
    for end, character in enumerate(text):
        counts[character] = counts.get(character, 0) + 1
        while len(counts) == needed:
            if not best or end - start + 1 < len(best):
                best = text[start : end + 1]
            leaving = text[start]
            counts[leaving] -= 1
            if counts[leaving] == 0:
                del counts[leaving]
            start += 1
    return best
