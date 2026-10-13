"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_run_with_k_distinct(text: str, k: int) -> int:
    """Return the length of the longest substring with at most `k` distinct
    characters.

    A window over the string and a count of each character inside it. The
    number of keys is the number of distinct characters, which is why a
    character's key is deleted the moment its count reaches zero: a key left
    behind at zero would make the window look fuller than it is.

    The left edge moves only while the window is over the limit, so after
    each step it is the longest valid window ending here. Both edges only
    move forward, so the whole scan is linear.
    """
    counts: dict[str, int] = {}
    best = 0
    start = 0
    for end, character in enumerate(text):
        counts[character] = counts.get(character, 0) + 1
        while len(counts) > k:
            leaving = text[start]
            counts[leaving] -= 1
            if counts[leaving] == 0:
                del counts[leaving]
            start += 1
        best = max(best, end - start + 1)
    return best
