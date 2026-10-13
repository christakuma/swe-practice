"""Reference solution. CI asserts this passes every test in `tests.py`."""

from collections import Counter


def longest_repeating_substring(text: str, k: int) -> int:
    """Return the length of the longest substring whose characters all repeat.

    A character with fewer than `k` copies in a piece of text has fewer than
    `k` in every part of that piece, so no qualifying substring can include
    it. Such a character is a wall: the answer, if it is in this piece at
    all, lies wholly between two walls. Cut the piece at every wall and each
    part is the same problem again -- with its own counts, because a
    character plentiful in the whole can be rare in a part.

    A piece with no walls qualifies as it stands.

    The pieces waiting to be examined are kept on a list and not on the call
    stack. Each cut removes at least one distinct character from the part,
    so the nesting is bounded by the number of distinct characters -- which
    is twenty-six for lower-case text and can be thousands here. `"aa"`,
    then that with one new character either side, then that with another,
    nests one level per character added.

    A part no longer than the best found so far is not worth queueing, which
    is the only pruning and is enough to keep the list short.
    """
    best = 0
    waiting = [text]
    while waiting:
        piece = waiting.pop()
        if len(piece) <= best:
            continue
        counts = Counter(piece)
        walls = {character for character, count in counts.items() if count < k}
        if not walls:
            best = len(piece)
            continue
        start = 0
        for position, character in enumerate(piece):
            if character in walls:
                if position - start > best:
                    waiting.append(piece[start:position])
                start = position + 1
        if len(piece) - start > best:
            waiting.append(piece[start:])
    return best
