"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_common_substring(first: str, second: str) -> int:
    """Return the length of the longest substring common to both strings.

    `run[j]` is the length of the common run ending at the current character
    of `first` and at `second[j - 1]`. A match extends the run that ended one
    step back in both strings; a mismatch ends it at zero. That reset is the
    whole difference from the subsequence table, which carries the best
    forward instead.

    One row is kept, over the shorter string. The answer is the largest
    entry ever written, since the best run can end anywhere.
    """
    if len(second) > len(first):
        first, second = second, first
    best = 0
    run = [0] * (len(second) + 1)
    for letter in first:
        previous = [0] * (len(second) + 1)
        previous, run = run, previous
        for column, other in enumerate(second, start=1):
            if letter == other:
                run[column] = previous[column - 1] + 1
                best = max(best, run[column])
    return best
