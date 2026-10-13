"""Reference solution. CI asserts this passes every test in `tests.py`."""


def top_k_frequent(words: list[str], k: int) -> list[str]:
    """Return the k most frequent words, ties broken by first appearance.

    Counted into a dict, whose keys stay in insertion order -- which is the
    order of first appearance. Python's sort is stable, so sorting those
    keys by count alone leaves equal counts in that order, and no explicit
    tie-break is needed.
    """
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts, key=lambda word: counts[word], reverse=True)
    return ranked[:k]
