"""Reference solution. CI asserts this passes every test in `tests.py`."""

import heapq
from itertools import pairwise


def alien_order(words: list[str]) -> str:
    """Return the alphabet implied by a list of sorted words.

    Three stages, and the first is where the problem actually lives.

    **Extracting the constraints.** Each adjacent pair of words yields exactly
    *one* fact: at the first position where they differ, the earlier word's
    character precedes the later one's. Everything after that position tells
    you nothing -- once the order is decided by an earlier character, later
    characters are unconstrained. Taking more than one edge per pair invents
    constraints that are not implied, which usually manufactures a cycle and
    reports "" for valid input.

    And if the two words agree throughout their common length, the shorter must
    come first. If it does not -- `["abc", "ab"]` -- the input is impossible,
    because no alphabet can sort a word before its own proper prefix. This is
    the case that is easy to miss entirely: it produces no edges at all, so a
    solution that only builds a graph and topologically sorts it returns a
    perfectly plausible ordering for input that cannot exist.

    **Deduplicating the edges.** The same pair can be implied by many word
    pairs. `successors` is a set per character for exactly that reason -- count
    an edge twice and the target's in-degree never reaches zero, so a valid
    input reports "".

    **Ordering.** The answer is a topological order (see `topological-order`),
    computed by Kahn's algorithm: repeatedly take a character with no
    unsatisfied predecessors. Using a **min-heap** rather than a plain queue is
    what delivers the lexicographically smallest valid order -- at every step
    the smallest currently-available character is taken, which is exactly the
    greedy choice that builds the smallest sequence. A plain deque gives a
    valid order that depends on insertion sequence, which is correct for the
    usual statement of this problem and untestable.

    A cycle shows up as characters never reaching in-degree zero, so the result
    is shorter than the alphabet.
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
            # No difference in the common prefix: the shorter must come first.
            if len(earlier) > len(later):
                return ""

    available = [character for character in characters if incoming[character] == 0]
    heapq.heapify(available)
    order: list[str] = []
    while available:
        character = heapq.heappop(available)
        order.append(character)
        for following in successors[character]:
            incoming[following] -= 1
            if incoming[following] == 0:
                heapq.heappush(available, following)

    return "".join(order) if len(order) == len(characters) else ""
