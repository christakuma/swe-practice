"""Reference solution. CI asserts this passes every test in `tests.py`."""


def heavy_hitters(words: list[str]) -> list[str]:
    """Return the words that make up more than a third of the list.

    Two passes and four variables.

    The first pass keeps two candidates, each with a counter. A word equal to
    a candidate raises its counter. A word that finds a counter at zero takes
    that slot over. A word that matches neither, with both slots occupied,
    lowers both counters -- which amounts to discarding three different
    words together: this one and one copy of each candidate. Discarding
    triples of different words can remove at most a third of the list's
    copies of any one word, so a word with more than a third always has a
    copy left standing in a slot at the end.

    The converse is false, so the second pass is not optional. The slots
    hold *something* whether or not any word is frequent enough, and the
    counters are not real counts. The candidates are counted properly and
    kept only if they clear the bar.

    The equality tests come before the zero tests, so a word already in one
    slot is never installed in the other.
    """
    first = second = None
    first_count = second_count = 0
    for word in words:
        if word == first:
            first_count += 1
        elif word == second:
            second_count += 1
        elif first_count == 0:
            first, first_count = word, 1
        elif second_count == 0:
            second, second_count = word, 1
        else:
            first_count -= 1
            second_count -= 1

    found = []
    for candidate in (first, second):
        if candidate is not None and 3 * sum(word == candidate for word in words) > len(
            words
        ):
            found.append(candidate)
    return sorted(found)
