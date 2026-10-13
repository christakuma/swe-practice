"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement

from solution import ListNode, merge_two_lists


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


def nodes_of(head: ListNode | None) -> list[ListNode]:
    found = []
    while head is not None:
        found.append(head)
        head = head.next
    return found


def test_merges_into_descending_order() -> None:
    """Returns every value from both lists, largest first."""
    result = merge_two_lists(linked([1, 3, 5]), linked([2, 4]))

    assert values_of(result) == [5, 4, 3, 2, 1]


def test_handles_empty_lists() -> None:
    """Reverses the other list when one is empty, and returns None for two."""
    assert values_of(merge_two_lists(None, linked([7, 8]))) == [8, 7]
    assert values_of(merge_two_lists(linked([7, 8]), None)) == [8, 7]
    assert merge_two_lists(None, None) is None


def test_keeps_every_duplicate() -> None:
    """Keeps equal values from both lists."""
    result = merge_two_lists(linked([1, 2, 2]), linked([2, 3]))

    assert values_of(result) == [3, 2, 2, 2, 1]


def test_agrees_with_sorting_for_every_pair_of_short_lists() -> None:
    """Matches a descending sort for every pair of short ascending lists."""
    lists = [
        list(chosen)
        for size in range(4)
        for chosen in combinations_with_replacement(range(4), size)
    ]
    for first in lists:
        for second in lists:
            result = merge_two_lists(linked(first), linked(second))
            assert values_of(result) == sorted(first + second, reverse=True)


def test_reuses_the_nodes_it_was_given() -> None:
    """Splices the original nodes rather than building new ones."""
    first, second = linked([1, 4]), linked([2, 3])
    originals = {id(node) for node in nodes_of(first) + nodes_of(second)}

    result = nodes_of(merge_two_lists(first, second))

    assert {id(node) for node in result} == originals
    assert [node.value for node in result] == [4, 3, 2, 1]


def test_merges_long_lists_without_recursing() -> None:
    """Merges two lists of twenty thousand nodes."""
    size = 20_000
    result = merge_two_lists(
        linked(list(range(0, 2 * size, 2))), linked(list(range(1, 2 * size, 2)))
    )

    assert values_of(result) == list(range(2 * size - 1, -1, -1))
