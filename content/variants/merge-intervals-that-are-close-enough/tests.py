"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement

from solution import merge_intervals


def by_grouping_pairs(
    intervals: list[tuple[int, int]], gap: int
) -> list[tuple[int, int]]:
    """The answer from the definition: join every close pair, then read off the groups.

    An oracle. It compares every pair of intervals and never sorts them, so
    it shares nothing with a sweep.
    """
    group = list(range(len(intervals)))

    def find(index: int) -> int:
        while group[index] != index:
            index = group[index]
        return index

    for first, (start_a, end_a) in enumerate(intervals):
        for second, (start_b, end_b) in enumerate(intervals):
            if max(start_a, start_b) - min(end_a, end_b) <= gap:
                group[find(first)] = find(second)

    spans: dict[int, tuple[int, int]] = {}
    for index, (start, end) in enumerate(intervals):
        root = find(index)
        low, high = spans.get(root, (start, end))
        spans[root] = (min(low, start), max(high, end))
    return sorted(spans.values())


def test_merges_intervals_within_the_gap() -> None:
    """Joins two intervals whose distance apart is no more than the gap."""
    assert merge_intervals([(1, 3), (5, 8), (20, 25)], 2) == [(1, 8), (20, 25)]


def test_a_distance_equal_to_the_gap_is_close_enough() -> None:
    """Merges at exactly the gap and not at one more."""
    assert merge_intervals([(1, 3), (6, 8)], 3) == [(1, 8)]
    assert merge_intervals([(1, 3), (6, 8)], 2) == [(1, 3), (6, 8)]


def test_a_gap_of_zero_merges_only_what_overlaps_or_touches() -> None:
    """Behaves as the original problem when the gap is zero."""
    assert merge_intervals([(1, 3), (4, 6)], 0) == [(1, 3), (4, 6)]
    assert merge_intervals([(1, 3), (3, 6)], 0) == [(1, 6)]
    assert merge_intervals([(1, 4), (2, 6)], 0) == [(1, 6)]


def test_handles_an_empty_list_and_a_single_interval() -> None:
    """Returns nothing for no intervals and the interval itself for one."""
    assert merge_intervals([], 5) == []
    assert merge_intervals([(4, 9)], 5) == [(4, 9)]


def test_merging_chains() -> None:
    """Joins a run of intervals each close to the next, however far apart the ends."""
    assert merge_intervals([(1, 2), (4, 5), (7, 8)], 2) == [(1, 8)]
    assert merge_intervals([(0, 0), (3, 3), (6, 6), (9, 9), (13, 13)], 3) == [
        (0, 9),
        (13, 13),
    ]


def test_the_result_is_not_widened_by_the_gap() -> None:
    """Returns the span the intervals cover, without the tolerance added on."""
    assert merge_intervals([(10, 12), (14, 15)], 5) == [(10, 15)]
    assert merge_intervals([(10, 12)], 5) == [(10, 12)]


def test_the_gap_is_not_counted_from_both_sides() -> None:
    """Does not merge intervals that are more than one gap apart.

    Widening each interval by the gap at both ends makes these two meet in
    the middle: they are four apart and the gap is two.
    """
    assert merge_intervals([(1, 3), (7, 9)], 2) == [(1, 3), (7, 9)]
    assert merge_intervals([(1, 3), (6, 9)], 2) == [(1, 3), (6, 9)]


def test_measures_from_the_furthest_end_reached() -> None:
    """Measures the distance from the end of the merged interval so far.

    (2, 3) sorts between the other two and ends at 3. The stretch being
    built already runs to 10, and it is from there that 12 is two away.
    """
    assert merge_intervals([(1, 10), (2, 3), (12, 13)], 2) == [(1, 13)]
    assert merge_intervals([(1, 10), (2, 3)], 0) == [(1, 10)]


def test_intervals_arrive_in_any_order() -> None:
    """Returns the same merged intervals, sorted, whatever the input order."""
    assert merge_intervals([(20, 25), (5, 8), (1, 3)], 2) == [(1, 8), (20, 25)]
    assert merge_intervals([(7, 8), (1, 2), (4, 5)], 2) == [(1, 8)]


def test_handles_negative_bounds_and_zero_length_intervals() -> None:
    """Merges across zero and treats a single point as an interval."""
    assert merge_intervals([(-9, -7), (-5, -5), (-2, 0)], 2) == [(-9, -5), (-2, 0)]
    assert merge_intervals([(-9, -7), (-5, -5), (-2, 0)], 3) == [(-9, 0)]


def test_a_large_gap_merges_everything() -> None:
    """Returns one interval when the gap exceeds every distance."""
    assert merge_intervals([(1, 2), (50, 60), (-40, -30)], 10**9) == [(-40, 60)]


def test_repeated_intervals_merge_into_one() -> None:
    """Returns a repeated interval once."""
    assert merge_intervals([(3, 5), (3, 5), (3, 5)], 0) == [(3, 5)]


def test_agrees_with_grouping_every_close_pair() -> None:
    """Matches the definition on every small set of intervals and every small gap.

    Every multiset of up to three intervals with bounds from 0 to 6, single
    points included, for gaps from zero to three.
    """
    spans = [(start, end) for start in range(7) for end in range(start, 7)]
    for count in range(4):
        for chosen in combinations_with_replacement(spans, count):
            intervals = list(reversed(chosen))
            for gap in range(4):
                expected = by_grouping_pairs(intervals, gap)

                assert merge_intervals(intervals, gap) == expected, (intervals, gap)


def test_handles_a_hundred_thousand_intervals() -> None:
    """Merges a hundred thousand intervals into sessions.

    Intervals of length three start every five, so they are two apart --
    except that every thousandth is missing, which leaves a hole of seven.
    A gap of two joins each run of 999 into one; a gap of one joins nothing;
    a gap of seven joins the lot.
    """
    count = 100_000
    intervals = [(5 * slot, 5 * slot + 3) for slot in range(count) if slot % 1_000]
    intervals.reverse()

    sessions = merge_intervals(intervals, 2)

    assert sessions == [
        (5_000 * block + 5, 5_000 * block + 4_998) for block in range(100)
    ]
    assert merge_intervals(intervals, 1) == sorted(intervals)
    assert merge_intervals(intervals, 7) == [(5, 5 * count - 2)]
