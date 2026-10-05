"""Reference solution. CI asserts this passes every test in `tests.py`."""


def three_sum(numbers: list[int]) -> list[tuple[int, int, int]]:
    """Return every distinct triple of values summing to zero.

    Sorting first is what makes everything else cheap. It costs O(n log n),
    which disappears next to the O(n^2) target, and it buys two separate
    things: a sorted range can be searched from both ends at once, and equal
    values end up adjacent, which turns deduplication into a comparison with
    the neighbour.

    With the first value fixed, the rest is a two-sum over the suffix for a
    known target -- and on sorted data that needs no hash map. Walk one pointer
    in from each end: if the pair sums too low the only way to increase it is
    to move `low` right, and if too high the only way to decrease it is to move
    `high` left. Every step eliminates one candidate for good, so the inner
    scan is linear and the whole thing is quadratic.

    **Deduplication is done by skipping, not by filtering afterwards.** Three
    places need it, and they are not the same place:

    - the fixed value, because a repeated first element can only re-find
      triples the earlier copy already found;
    - `low` and `high` after recording a hit, because other copies of those two
      values would rebuild the identical triple.

    Collecting everything into a set and sorting at the end also works and is
    a reasonable answer -- but it allocates proportional to the number of
    *candidate* hits rather than distinct ones, and it hides the reason the
    duplicates arise. Skipping is O(1) space and says what it means.

    The early `break` is not just an optimisation. Once the fixed value is
    positive the whole suffix is positive too -- it is sorted -- so no triple
    starting here can reach zero, and every later fixed value is worse.
    """
    numbers = sorted(numbers)
    size = len(numbers)
    triples: list[tuple[int, int, int]] = []

    for first in range(size - 2):
        if numbers[first] > 0:
            break
        if first > 0 and numbers[first] == numbers[first - 1]:
            continue

        low, high = first + 1, size - 1
        while low < high:
            total = numbers[first] + numbers[low] + numbers[high]
            if total < 0:
                low += 1
            elif total > 0:
                high -= 1
            else:
                triples.append((numbers[first], numbers[low], numbers[high]))
                low += 1
                high -= 1
                while low < high and numbers[low] == numbers[low - 1]:
                    low += 1
                while low < high and numbers[high] == numbers[high + 1]:
                    high -= 1

    return triples
