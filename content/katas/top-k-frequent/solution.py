"""Reference solution. CI asserts this passes every test in `tests.py`."""

from collections import Counter


def top_k_frequent(words: list[str], k: int) -> list[str]:
    """Return the k most frequent words, most frequent first.

    Counting is the easy half. The interesting half is the tie-break, and it is
    the reason `Counter.most_common` is not the answer: it orders equal counts by
    first insertion, which is a real and useful guarantee and not the one asked
    for here. Sorting explicitly says what the order is.

    `(-count, word)` is the key worth internalising. Python sorts tuples
    lexicographically and ascending only, so negating the count is how you get
    descending counts and ascending words out of a single ascending sort -- no
    `reverse=True`, which would reverse the tie-break too and give reverse
    alphabetical.

    O(n log n) in the number of *distinct* words. A heap of size k gets the
    asymptotics down to O(n log k), which matters when k is small and the
    vocabulary is large; `heapq.nsmallest(k, ...)` with the same key does it in
    one line and is the version to reach for then.
    """
    counts = Counter(words)
    ranked = sorted(counts, key=lambda word: (-counts[word], word))
    return ranked[:k]
