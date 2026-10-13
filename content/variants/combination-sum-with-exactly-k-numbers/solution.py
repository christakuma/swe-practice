"""Reference solution. CI asserts this passes every test in `tests.py`."""


def combination_sum(
    candidates: list[int], target: int, count: int
) -> list[tuple[int, ...]]:
    """Return every combination of exactly `count` candidates summing to `target`.

    The standard search with a second counter running down beside the first.
    A combination is finished when *both* reach zero together; either one
    reaching zero alone is a dead end.

    The index rule is unchanged -- recurse from `index`, not `index + 1`, so a
    candidate can repeat but an earlier one never returns -- and so is what it
    buys: each multiset is built along exactly one path.

    The prune is stronger than before. Every number still to be chosen is at
    least `candidate`, so the least that can still be added is
    `left * candidate`; once that overshoots, this candidate and every larger
    one are finished.
    """
    ordered = sorted(candidates)
    results: list[tuple[int, ...]] = []
    chosen: list[int] = []

    def search(start: int, remaining: int, left: int) -> None:
        if left == 0:
            if remaining == 0:
                results.append(tuple(chosen))
            return
        for index in range(start, len(ordered)):
            candidate = ordered[index]
            if candidate * left > remaining:
                break
            chosen.append(candidate)
            search(index, remaining - candidate, left - 1)
            chosen.pop()

    search(0, target, count)
    return results
