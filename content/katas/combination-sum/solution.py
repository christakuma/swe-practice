"""Reference solution. CI asserts this passes every test in `tests.py`."""


def combination_sum(candidates: list[int], target: int) -> list[tuple[int, ...]]:
    """Return every distinct combination of candidates summing to `target`.

    Backtracking: choose candidates one at a time, subtracting from the target.
    A remaining target of exactly zero is a complete answer; going below zero
    is a dead end.

    **The index rule is what makes these combinations rather than
    permutations.** Recursing with `start=index` allows the *same* candidate
    again -- which is what "use as many times as you like" needs -- while never
    going back to an earlier one. That enforces non-decreasing order, so each
    multiset is constructed by exactly one path through the search and no
    deduplication is required anywhere.

    Contrast with `three-sum-to-zero`, where duplicates had to be skipped
    explicitly in three places. Here the same job is done by the shape of the
    recursion. That is the better kind of fix: **prevent the duplicate rather
    than detect it**, which is the same preference as generating only
    palindromes in `longest-palindromic-substring` instead of filtering for
    them.

    `chosen` is mutated and restored around the recursive call -- append,
    recurse, pop -- which is the choose/recurse/un-choose skeleton from
    `find-a-word-in-a-grid`. The tuple is snapshotted on success, because
    `chosen` keeps changing afterwards.

    Sorting first buys the `break`: once a candidate exceeds the remaining
    target, every later one does too, so the loop stops rather than testing
    each in turn. Without sorting it would have to be a `continue`, which still
    works and explores more.

    A target of zero returns `[()]` -- one combination, the empty one -- which
    falls out of the base case rather than needing a special case. Worth
    noticing it is not `[]`: "no ways" and "one way, which is to do nothing"
    are different answers, and the second is correct here.
    """
    ordered = sorted(candidates)
    results: list[tuple[int, ...]] = []
    chosen: list[int] = []

    def search(start: int, remaining: int) -> None:
        if remaining == 0:
            results.append(tuple(chosen))
            return
        for index in range(start, len(ordered)):
            candidate = ordered[index]
            if candidate > remaining:
                break  # sorted, so every later candidate is too large as well
            chosen.append(candidate)
            search(index, remaining - candidate)
            chosen.pop()

    search(0, target)
    return sorted(results)
