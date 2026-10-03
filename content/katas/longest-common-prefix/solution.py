"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_common_prefix(words: list[str]) -> str:
    """Return the longest string that every word starts with.

    The prefix can only shrink, which is the observation that makes this one
    pass: start with the first word as the candidate and cut it back against each
    other word. Once it is empty nothing can grow it again, so the loop can stop.

    Comparing character-by-character across all words in lockstep is the other
    standard shape and is better on its best case -- it stops at the first
    differing column rather than after scanning a whole word. It is also where
    the index-out-of-range bugs live, because one word being shorter than the
    column you are reading is the thing that ends the prefix.

    `str.startswith` keeps the slicing in C and makes the termination condition
    visible. The early return matters for the degenerate input: a single empty
    string among a thousand long ones ends the answer immediately.
    """
    if not words:
        return ""

    prefix = words[0]
    for word in words[1:]:
        while not word.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix
