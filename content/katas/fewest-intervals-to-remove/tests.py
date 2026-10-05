"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement, pairwise

from solution import fewest_removals


def reference(intervals: list[tuple[int, int]]) -> int:
    """Fewest removals by trying every subset -- an independent oracle.

    It searches for the largest compatible subset outright, so it shares no
    sort key and no greedy argument with the intended solution. Exponential,
    and fine at these sizes.
    """
    size = len(intervals)
    best = 0
    for mask in range(1 << size):
        chosen = sorted(intervals[i] for i in range(size) if mask >> i & 1)
        if all(a[1] <= b[0] for a, b in pairwise(chosen)):
            best = max(best, len(chosen))
    return size - best


def test_handles_the_worked_example() -> None:
    """Returns one removal for the documented input.

    Worth knowing this case does *not* separate sorting by end from sorting by
    start -- both give 1. The counter-examples below are the ones that do.
    """
    assert fewest_removals([(1, 2), (2, 3), (3, 4), (1, 3)]) == 1


def test_sorts_by_end_rather_than_start() -> None:
    """Keeps the two short intervals rather than the one long one.

    The discriminating case for the whole kata. (1, 100) starts first and
    blocks everything behind it, so a start-ordered greedy keeps one interval
    and removes two. Ordering by end keeps both short ones and removes one.
    """
    assert fewest_removals([(1, 100), (2, 3), (3, 4)]) == 1


def test_sorts_by_end_on_a_starker_case() -> None:
    """Keeps three short intervals rather than one long one.

    Same failure, wider margin: a start-ordered greedy removes three where one
    is enough.
    """
    assert fewest_removals([(1, 10), (2, 3), (4, 5), (6, 7)]) == 1


def test_handles_duplicates() -> None:
    """Keeps one of several identical intervals."""
    assert fewest_removals([(1, 2), (1, 2), (1, 2)]) == 2
    assert fewest_removals([(1, 2), (1, 2)]) == 1


def test_handles_already_disjoint_intervals() -> None:
    """Removes nothing when nothing overlaps."""
    assert fewest_removals([(1, 2), (3, 4), (5, 6)]) == 0
    assert fewest_removals([(1, 2)]) == 0


def test_handles_an_empty_list() -> None:
    """Returns 0 for no intervals."""
    assert fewest_removals([]) == 0


def test_treats_touching_as_compatible() -> None:
    """Keeps both intervals when they merely meet at a point.

    (1, 2) and (2, 3) share an endpoint and do not overlap, so nothing needs
    removing. A solution using a strict comparison removes one.
    """
    assert fewest_removals([(1, 2), (2, 3)]) == 0
    assert fewest_removals([(1, 2), (2, 3), (3, 4), (4, 5)]) == 0


def test_handles_nested_intervals() -> None:
    """Keeps the inner interval when one contains another."""
    assert fewest_removals([(1, 10), (2, 3)]) == 1
    assert fewest_removals([(1, 10), (2, 9), (3, 8)]) == 2


def test_handles_a_chain_of_overlaps() -> None:
    """Handles a staircase where each interval overlaps the next.

    Four intervals each overlapping its neighbour, and only two can survive --
    (1, 3) and (3, 5), which touch. Taking (2, 4) instead of (3, 5) after
    (1, 3) is impossible, so the staircase costs two removals rather than one.
    """
    assert fewest_removals([(1, 3), (2, 4), (3, 5), (4, 6)]) == 2


def test_handles_unsorted_input() -> None:
    """Gives the same answer however the intervals are ordered."""
    intervals = [(3, 4), (1, 100), (2, 3)]

    assert fewest_removals(intervals) == 1
    assert fewest_removals(list(reversed(intervals))) == 1


def test_handles_zero_width_intervals() -> None:
    """Handles intervals whose start equals their end.

    Two identical zero-width intervals need *no* removals, which is worth
    staring at: under "touching does not overlap", (1, 1) and (1, 1) satisfy
    `start >= last_end` and so coexist. Surprising, consistent, and a direct
    consequence of the closed-interval convention rather than a special case --
    half-open intervals would say the same thing, since neither contains any
    point at all.
    """
    assert fewest_removals([(1, 1), (1, 1)]) == 0
    assert fewest_removals([(1, 1), (2, 2)]) == 0
    assert fewest_removals([(1, 5), (2, 2)]) == 1


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool."""
    assert type(fewest_removals([(1, 2)])) is int


def test_does_not_mutate_the_input() -> None:
    """Leaves the caller's list in its original order.

    Sorting is the right first move and `intervals.sort()` is the wrong way to
    do it.
    """
    intervals = [(3, 4), (1, 100), (2, 3)]
    before = list(intervals)

    fewest_removals(intervals)

    assert intervals == before


def test_agrees_with_a_subset_search_on_every_small_input() -> None:
    """Matches an exhaustive subset search for every small interval list.

    Every multiset of up to four intervals over a small coordinate range --
    about three thousand cases. The sort key is a greedy choice, and greedy
    choices fail on particular shapes rather than particular sizes.
    """
    pool = [(start, end) for start in range(4) for end in range(start, 5)]
    for size in range(5):
        for chosen in combinations_with_replacement(pool, size):
            intervals = list(chosen)

            assert fewest_removals(intervals) == reference(intervals), intervals


def test_handles_a_large_input() -> None:
    """Handles two hundred thousand intervals within the time limit.

    Half are unit intervals that can all be kept; half are long ones spanning
    everything, which must all go.
    """
    units = [(value * 2, value * 2 + 1) for value in range(100_000)]
    spanners = [(0, 200_000) for _ in range(100_000)]

    assert fewest_removals(units + spanners) == 100_000
