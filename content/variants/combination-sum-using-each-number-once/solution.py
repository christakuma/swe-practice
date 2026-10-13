"""Reference solution. CI asserts this passes every test in `tests.py`."""


def combination_sum(candidates: list[int], target: int) -> list[tuple[int, ...]]:
    """Return every distinct combination summing to `target`, using each
    candidate at most once.

    Sorted, then searched depth-first. Two things differ from the version
    that allows reuse, and each is one expression:

    * the recursion continues from `index + 1`, so a candidate is not offered
      to the combination it is already in;
    * `index > start and value == ordered[index - 1]` skips a value that has
      already been tried *at this depth*. The first copy of a value explores
      every combination that uses it here; a second copy in the same position
      would only find them again.

    That skip is what makes the result free of duplicates without a set, and
    what keeps thirty equal candidates from costing two to the thirty.
    Sorting also lets the loop stop at the first candidate that is too big,
    and makes the results come out already in order.
    """
    ordered = sorted(candidates)
    found: list[tuple[int, ...]] = []
    chosen: list[int] = []

    def extend(start: int, remaining: int) -> None:
        if remaining == 0:
            found.append(tuple(chosen))
            return
        for index in range(start, len(ordered)):
            value = ordered[index]
            if value > remaining:
                break
            if index > start and value == ordered[index - 1]:
                continue
            chosen.append(value)
            extend(index + 1, remaining - value)
            chosen.pop()

    extend(0, target)
    return found
