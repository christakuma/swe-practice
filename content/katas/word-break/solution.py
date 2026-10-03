"""Reference solution. CI asserts this passes every test in `tests.py`."""


def can_segment(text: str, words: list[str]) -> bool:
    """Whether `text` can be split into a sequence of words from `words`.

    `reachable[i]` means "the first i characters can be segmented". The empty
    prefix is reachable, and position i is reachable when some earlier reachable
    position j has `text[j:i]` in the dictionary.

    Greedy fails, which is what makes this worth drilling: matching the longest
    word at each step takes `cats` out of `catsandog`, leaving `andog`, and
    reports failure -- while `cat` + `sand` + `og` also fails and `cats` + `and`
    + `og` fails, so this particular input is genuinely unsegmentable. The input
    that kills greedy is `cars` with `["car", "ca", "rs"]`: the longest match is
    `car`, leaving `s`, which is not a word -- and `ca` + `rs` works. Greedy has
    no way back.

    A `set` for the dictionary, because the inner loop asks "is this slice a
    word" once per pair of positions. With a list it is a linear scan each time
    and the whole thing gains a factor of the dictionary size.

    O(n^2) slices, each costing O(n) to cut and hash, so O(n^3) in the length of
    the text in the worst case. Bounding the inner loop by the longest word in
    the dictionary is the easy improvement and is what makes it practical on real
    text, where words are short and the string is long.
    """
    dictionary = set(words)
    longest = max((len(word) for word in dictionary), default=0)

    reachable = [True] + [False] * len(text)
    for end in range(1, len(text) + 1):
        for start in range(max(0, end - longest), end):
            if reachable[start] and text[start:end] in dictionary:
                reachable[end] = True
                break
    return reachable[len(text)]
