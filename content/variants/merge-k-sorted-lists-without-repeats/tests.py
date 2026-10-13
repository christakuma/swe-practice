"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement, product

from solution import ListNode, merge_k_lists


def linked(values: list[int]) -> ListNode | None:
    """A list holding `values` in order."""
    head = None
    for value in reversed(values):
        head = ListNode(value, head)
    return head


def values_of(head: ListNode | None) -> list[int]:
    """The values in order, refusing to walk a list that does not end."""
    found: list[int] = []
    while head is not None:
        assert len(found) < 1_000_000, "the list does not end"
        found.append(head.value)
        head = head.next
    return found


def test_drops_values_repeated_across_lists() -> None:
    """Keeps one of each value that appears in several lists."""
    lists = [linked([1, 4, 5]), linked([1, 3, 4]), linked([2, 6])]

    assert values_of(merge_k_lists(lists)) == [1, 2, 3, 4, 5, 6]


def test_drops_values_repeated_inside_one_list() -> None:
    """Keeps one of each value repeated within a single list."""
    assert values_of(merge_k_lists([linked([2, 2, 2])])) == [2]
    assert values_of(merge_k_lists([linked([1, 1, 2, 3, 3])])) == [1, 2, 3]


def test_handles_nothing_to_merge() -> None:
    """Returns None for no lists, and for lists that are all empty."""
    assert merge_k_lists([]) is None
    assert merge_k_lists([None, None]) is None


def test_ends_the_list_after_the_last_distinct_value() -> None:
    """Leaves the last node pointing at nothing.

    The largest value is repeated, so the node that is kept still has a
    duplicate linked after it unless the tail is cut.
    """
    assert values_of(merge_k_lists([linked([1, 5, 5]), linked([5])])) == [1, 5]


def test_agrees_with_a_sorted_set_for_every_small_input() -> None:
    """Matches the sorted distinct values for every trio of short lists."""
    pool = [
        list(chosen)
        for size in range(3)
        for chosen in combinations_with_replacement(range(3), size)
    ]
    for chosen in product(pool, repeat=3):
        lists = [linked(values) for values in chosen]
        expected = sorted({value for values in chosen for value in values})
        assert values_of(merge_k_lists(lists)) == expected, chosen


def test_reuses_the_nodes_it_was_given() -> None:
    """Returns nodes that were in the input, not new ones."""
    lists = [linked([1, 2]), linked([2, 3])]
    originals = set()
    for head in lists:
        node = head
        while node is not None:
            originals.add(id(node))
            node = node.next

    node = merge_k_lists(lists)
    while node is not None:
        assert id(node) in originals
        node = node.next


def test_merges_a_thousand_lists() -> None:
    """Merges a thousand lists of a hundred nodes within the time limit."""
    lists = [linked(list(range(start, start + 100))) for start in range(1000)]

    assert values_of(merge_k_lists(lists)) == list(range(1099))
