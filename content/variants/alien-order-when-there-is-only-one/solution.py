"""Reference solution. CI asserts this passes every test in `tests.py`."""

from itertools import pairwise


def alien_order(words: list[str]) -> str:
    """Return the alphabet a list of sorted words implies, if only one fits.

    The graph is the standard one: each adjacent pair of words gives one edge,
    from the first position where they differ, and a word followed by its own
    proper prefix is impossible.

    Kahn's algorithm then answers both questions at once. `available` holds
    the characters with nothing left to wait for. Empty before every
    character is placed means a cycle. **Two or more means a choice**, and a
    choice is two alphabets: either of them can go next and both orders
    complete. So the loop runs only while there is exactly one, and anything
    that stops it early -- none or several -- leaves `order` short.

    No heap is needed, because a unique order has no ties to break.
    """
    characters = {character for word in words for character in word}
    successors: dict[str, set[str]] = {character: set() for character in characters}
    incoming = dict.fromkeys(characters, 0)

    for earlier, later in pairwise(words):
        for first, second in zip(earlier, later, strict=False):
            if first != second:
                if second not in successors[first]:
                    successors[first].add(second)
                    incoming[second] += 1
                break
        else:
            if len(earlier) > len(later):
                return ""

    available = [character for character in characters if incoming[character] == 0]
    order: list[str] = []
    while len(available) == 1:
        character = available.pop()
        order.append(character)
        for following in successors[character]:
            incoming[following] -= 1
            if incoming[following] == 0:
                available.append(following)

    return "".join(order) if len(order) == len(characters) else ""
