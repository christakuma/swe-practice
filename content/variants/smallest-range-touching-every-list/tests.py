"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement, product

from solution import ListNode, smallest_range


def build(values: list[int]) -> ListNode | None:
    head: ListNode | None = None
    for value in reversed(values):
        head = ListNode(value, head)
    return head


def read(head: ListNode | None) -> list[int]:
    values = []
    while head is not None:
        values.append(head.value)
        head = head.next
    return values


def solve(rows: list[list[int]]) -> tuple[int, int] | None:
    return smallest_range([build(row) for row in rows])


def by_trying_every_low_end(rows: list[list[int]]) -> tuple[int, int] | None:
    """The answer by taking each value as the low end in turn. An oracle.

    For a given low end, the high end has to reach the first value at or
    above it in every list. No heap, and no merging.
    """
    if not rows or any(not row for row in rows):
        return None
    best: tuple[int, int] | None = None
    for low in sorted({value for row in rows for value in row}):
        reaches = [
            min((value for value in row if value >= low), default=None) for row in rows
        ]
        if any(reach is None for reach in reaches):
            continue
        high = max(reach for reach in reaches if reach is not None)
        if best is None or high - low < best[1] - best[0]:
            best = (low, high)
    return best


def test_finds_the_narrowest_range_across_three_lists() -> None:
    """Returns the range spanning the closest values, one from each list."""
    rows = [[4, 10, 15, 24, 26], [0, 9, 12, 20], [5, 18, 22, 30]]

    assert solve(rows) == (20, 24)


def test_a_value_in_every_list_gives_a_range_of_one_point() -> None:
    """Returns the same value for both ends when every list holds it."""
    assert solve([[1, 5, 9], [5, 7]]) == (5, 5)
    assert solve([[1, 2, 3], [1, 2, 3], [1, 2, 3]]) == (1, 1)


def test_a_single_list_gives_its_first_value() -> None:
    """Returns the first value twice when there is only one list."""
    assert solve([[3, 8, 9]]) == (3, 3)
    assert solve([[7]]) == (7, 7)


def test_returns_none_without_lists_or_with_an_empty_one() -> None:
    """Returns None when there is nothing to touch or a list that cannot be touched."""
    assert smallest_range([]) is None
    assert smallest_range([None]) is None
    assert solve([[1, 2], []]) is None
    assert solve([[], [1, 2], [3]]) is None


def test_the_range_is_not_always_at_the_front_of_the_lists() -> None:
    """Looks past the first value of each list."""
    assert solve([[1, 50], [20, 51], [40, 52]]) == (50, 52)
    assert solve([[1, 2, 3, 90], [91], [89, 200]]) == (89, 91)


def test_keeps_the_smallest_low_end_among_equally_narrow_ranges() -> None:
    """Returns the earlier of two ranges of the same width."""
    assert solve([[1, 10], [2, 11]]) == (1, 2)
    assert solve([[1, 5, 9], [2, 6, 10]]) == (1, 2)
    assert solve([[0, 20, 40], [3, 23, 43], [1, 21, 41]]) == (0, 3)


def test_stops_when_the_list_with_the_smallest_value_runs_out() -> None:
    """Does not carry on with the remaining lists once one is exhausted.

    After the first list's 2 there is nothing more of it. The 30 and 31 are
    closer together than anything involving 2, but a range around them
    leaves the first list out.
    """
    assert solve([[1, 2], [10, 30], [20, 31]]) == (2, 20)
    assert solve([[5], [1, 4, 100, 101], [2, 100, 101]]) == (2, 5)


def test_the_high_end_follows_values_as_they_are_brought_in() -> None:
    """Widens the range when advancing a list brings in a larger value.

    The largest of the three fronts is 6. Advancing the first list brings in
    100, and the range under consideration must stretch to it.
    """
    assert solve([[1, 100], [5, 201], [6, 302]]) == (1, 6)
    assert solve([[1, 100], [5, 7], [6, 8]]) == (1, 6)
    assert solve([[1, 9], [5, 8], [6, 7]]) == (7, 9)


def test_handles_repeated_values_and_negatives() -> None:
    """Handles lists that repeat a value and lists that go below zero."""
    assert solve([[-5, -5, -1], [-3, 4], [-2, -2, 9]]) == (-3, -1)
    assert solve([[2, 2, 2], [2, 2]]) == (2, 2)
    assert solve([[-10, 10], [0, 0, 0]]) == (-10, 0)


def test_leaves_the_lists_as_they_were() -> None:
    """Does not relink or consume the lists it reads."""
    heads = [build([4, 10, 15]), build([0, 9, 12]), build([5, 18])]

    smallest_range(heads)

    assert [read(head) for head in heads] == [[4, 10, 15], [0, 9, 12], [5, 18]]


def test_agrees_with_trying_every_low_end() -> None:
    """Matches a search over every low end for every small set of lists.

    Every list of one or two values from 0 to 5, in every combination of
    one, two and three lists.
    """
    rows = [
        list(row)
        for size in (1, 2)
        for row in combinations_with_replacement(range(6), size)
    ]
    for count in (1, 2, 3):
        for chosen in product(rows, repeat=count):
            expected = by_trying_every_low_end(list(chosen))

            assert solve(list(chosen)) == expected, chosen


def test_agrees_with_trying_every_low_end_on_longer_lists() -> None:
    """Matches the same search on three lists of three values each."""
    rows = [list(row) for row in combinations_with_replacement(range(0, 14, 2), 3)]
    for first in rows[::5]:
        for second in rows[1::7]:
            third = [value + 1 for value in first[::-1]][::-1]
            expected = by_trying_every_low_end([first, second, third])

            assert solve([first, second, third]) == expected, (first, second, third)


def test_handles_a_thousand_lists_of_a_hundred_nodes() -> None:
    """Finds the range across a hundred thousand nodes.

    List i holds ninety-nine values ten thousand apart, offset by 3 * i, and
    one more near half a million: 500,000 plus i's remainder on division by
    five. The offsets spread the regular values over three thousand, so the
    only place every list comes within a few of every other is that one.
    """
    rows = []
    for index in range(1_000):
        regular = [3 * index + 10_000 * step for step in range(99)]
        rows.append(sorted([*regular, 500_000 + index % 5]))

    assert solve(rows) == (500_000, 500_004)
