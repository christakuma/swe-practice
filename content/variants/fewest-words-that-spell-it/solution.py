"""Reference solution. CI asserts this passes every test in `tests.py`."""

import math


def fewest_words(text: str, words: list[str]) -> int:
    """Return the fewest dictionary words that `text` splits into.

    The word-break table with numbers in place of booleans. `fewest[end]` is
    the smallest number of words spelling the first `end` characters, or
    infinity if they cannot be spelled.

    Each entry looks back over every length a dictionary word could have: if
    the last `size` characters of the prefix are a word, one way to spell the
    prefix is to spell what comes before and add that word. The minimum over
    all such ways is kept.

    Infinity is doing the work a flag would otherwise do. `inf + 1` is still
    `inf`, so an unspellable prefix cannot make a later one look spellable,
    and it never wins a `min`.
    """
    known = set(words)
    sizes = sorted({len(word) for word in known})
    fewest = [0.0] + [math.inf] * len(text)
    for end in range(1, len(text) + 1):
        for size in sizes:
            if size > end:
                break
            if text[end - size : end] in known:
                fewest[end] = min(fewest[end], fewest[end - size] + 1)
    return -1 if fewest[-1] == math.inf else int(fewest[-1])
