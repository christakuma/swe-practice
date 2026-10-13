"""Reference solution. CI asserts this passes every test in `tests.py`."""

from itertools import pairwise


def longest_shared_prefix(words: list[str]) -> str:
    """Return the longest prefix shared by at least two of the words.

    In sorted order the two words sharing the longest prefix are adjacent:
    anything sorting between them begins with that same prefix. So only
    neighbours are compared. Candidates are ranked by length first and then
    alphabetically, which is the tie rule.
    """
    best = ""
    for first, second in pairwise(sorted(words)):
        length = 0
        while (
            length < len(first)
            and length < len(second)
            and first[length] == second[length]
        ):
            length += 1
        candidate = first[:length]
        if (-len(candidate), candidate) < (-len(best), best):
            best = candidate
    return best
