"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_segmentations(text: str, words: list[str]) -> int:
    """Count the ways `text` splits into a sequence of words from `words`.

    `ways[end]` is the number of splits of the first `end` characters. Each
    one finishes with some dictionary word, so it is the sum of
    `ways[end - len(word)]` over the words that end there. Only lengths up to
    the longest word are tried, and the words are held in a set, which is
    also what stops a repeated word being counted twice.
    """
    known = set(words)
    longest = max((len(word) for word in known), default=0)
    ways = [1] + [0] * len(text)
    for end in range(1, len(text) + 1):
        for length in range(1, min(longest, end) + 1):
            if ways[end - length] and text[end - length : end] in known:
                ways[end] += ways[end - length]
    return ways[len(text)]
