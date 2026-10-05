"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise

from solution import ListNode, merge_k_lists


def build(values: list[int]) -> ListNode | None:
    """Return the head of a list over `values`."""
    nodes = [ListNode(value) for value in values]
    for node, following in pairwise(nodes):
        node.next = following
    return nodes[0] if nodes else None


def walk(head: ListNode | None, limit: int = 1_000_000) -> list[int]:
    """Read the values out, refusing to loop forever on a cyclic list."""
    values: list[int] = []
    node = head
    while node is not None:
        if len(values) > limit:
            raise AssertionError("the list does not terminate -- it is cyclic")
        values.append(node.value)
        node = node.next
    return values


def test_merges_three_lists() -> None:
    """Returns every value from every list in sorted order."""
    lists = [build([1, 4, 5]), build([1, 3, 4]), build([2, 6])]

    assert walk(merge_k_lists(lists)) == [1, 1, 2, 3, 4, 4, 5, 6]


def test_handles_no_lists_at_all() -> None:
    """Returns an empty list when given no lists."""
    assert merge_k_lists([]) is None


def test_handles_every_list_empty() -> None:
    """Returns an empty list when every input list is empty."""
    assert merge_k_lists([None, None, None]) is None


def test_handles_a_single_list() -> None:
    """Returns the one list it was given."""
    assert walk(merge_k_lists([build([1, 2, 3])])) == [1, 2, 3]


def test_skips_empty_lists_among_full_ones() -> None:
    """Ignores None entries mixed in with real lists.

    Seeding the heap without the None check raises AttributeError here, and
    nothing in the tests above has a gap to catch it.
    """
    lists = [None, build([2, 5]), None, build([1, 3]), None]

    assert walk(merge_k_lists(lists)) == [1, 2, 3, 5]


def test_handles_equal_values_across_lists() -> None:
    """Merges lists whose values are all equal.

    Every comparison is a tie, so a heap entry of (value, node) gets as far as
    comparing two ListNodes and raises TypeError. A tiebreaker between the
    value and the node is what makes this pass.
    """
    lists = [build([1, 1]), build([1, 1]), build([1, 1])]

    assert walk(merge_k_lists(lists)) == [1, 1, 1, 1, 1, 1]


def test_handles_lists_of_very_different_lengths() -> None:
    """Drains a long list after the short ones are exhausted."""
    lists = [build([1]), build([2]), build(list(range(3, 50)))]

    assert walk(merge_k_lists(lists)) == list(range(1, 50))


def test_handles_disjoint_ranges() -> None:
    """Concatenates lists whose ranges do not overlap."""
    lists = [build([7, 8]), build([1, 2]), build([4, 5])]

    assert walk(merge_k_lists(lists)) == [1, 2, 4, 5, 7, 8]


def test_handles_negative_values() -> None:
    """Merges across negative and positive values."""
    lists = [build([-5, 2]), build([-9, -1]), build([0])]

    assert walk(merge_k_lists(lists)) == [-9, -5, -1, 0, 2]


def test_reuses_the_nodes_it_was_given() -> None:
    """Splices the original nodes rather than building new ones."""
    first = build([1, 3])
    second = build([2, 4])

    result = merge_k_lists([first, second])

    assert result is first
    assert result.next is second


def test_terminates_rather_than_running_into_a_source_list() -> None:
    """Returns a list that ends.

    Each emitted node still points into its own source list until the next
    append overwrites that pointer, so an off-by-one at the end can leave the
    result running back into the middle of an input.
    """
    lists = [build([1, 2]), build([3, 4])]

    assert walk(merge_k_lists(lists), limit=10) == [1, 2, 3, 4]


def test_merges_many_lists_without_rewalking_an_accumulator() -> None:
    """Merges a thousand lists of a hundred nodes within the time limit.

    One hundred thousand nodes across k = 1000 lists. Folding a two-list merge
    over the collection rewalks a growing accumulation each time -- about fifty
    million node visits, which is seconds. The heap makes it log k per node.
    """
    size = 100
    count = 1_000
    lists = [
        build([value * count + offset for value in range(size)])
        for offset in range(count)
    ]

    result = walk(merge_k_lists(lists))

    assert len(result) == size * count
    assert result == sorted(result)
    assert result[0] == 0
    assert result[-1] == (size - 1) * count + count - 1
