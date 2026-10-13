"""Reference solution. CI asserts this passes every test in `tests.py`."""

from collections import Counter


def longest_palindrome(text: str) -> str:
    """Return the longest palindrome buildable from the characters of `text`.

    Positions in a palindrome mirror each other, so characters are spent in
    pairs -- one each side -- with at most one left to stand alone in the
    middle. Each character therefore gives `count // 2` pairs, and the length
    is twice the number of pairs, plus one if any character has an odd count.

    A longest palindrome has no choice about *which* pairs it uses: all of
    them. Its only freedoms are the order of the left half and, when several
    characters have one to spare, which of them is the centre.

    Two strings of equal length are compared from the left, so the left half
    is decided first and sorted order is the smallest it can be. The centre
    comes next and the smallest spare character wins it. The right half is
    the left half reversed and has no say.

    A character with an *even* count is never the centre. Putting one there
    would break up a pair to do it, and the palindrome would be shorter.
    """
    counts = Counter(text)
    half = "".join(character * (counts[character] // 2) for character in sorted(counts))
    spare = [character for character, count in counts.items() if count % 2]
    return half + min(spare, default="") + half[::-1]
