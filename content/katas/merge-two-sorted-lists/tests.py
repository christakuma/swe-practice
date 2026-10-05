"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise

from solution import ListNode, merge_two_lists


def build(values: list[int]) -> tuple[ListNode | None, list[ListNode]]:
    """Return the head of a list over `values`, and every node in order."""
    nodes = [ListNode(value) for value in values]
    for node, following in pairwise(nodes):
        node.next = following
    return (nodes[0] if nodes else None), nodes


def walk(head: ListNode | None, limit: int = 100_000) -> list[int]:
    """Read the values out, refusing to loop forever on a cyclic list."""
    values: list[int] = []
    node = head
    while node is not None:
        if len(values) > limit:
            raise AssertionError("the list does not terminate -- it is cyclic")
        values.append(node.value)
        node = node.next
    return values


def test_interleaves_two_lists() -> None:
    """Returns every value from both lists in sorted order."""
    first, _ = build([1, 3, 5])
    second, _ = build([2, 4])

    assert walk(merge_two_lists(first, second)) == [1, 2, 3, 4, 5]


def test_handles_both_lists_empty() -> None:
    """Returns an empty list when both inputs are empty."""
    assert merge_two_lists(None, None) is None


def test_handles_the_first_list_empty() -> None:
    """Returns the second list when the first is empty."""
    second, _ = build([1, 2, 3])

    assert walk(merge_two_lists(None, second)) == [1, 2, 3]


def test_handles_the_second_list_empty() -> None:
    """Returns the first list when the second is empty."""
    first, _ = build([1, 2, 3])

    assert walk(merge_two_lists(first, None)) == [1, 2, 3]


def test_handles_lists_that_do_not_overlap() -> None:
    """Appends one list after the other when their ranges are disjoint."""
    first, _ = build([1, 2, 3])
    second, _ = build([7, 8, 9])

    assert walk(merge_two_lists(first, second)) == [1, 2, 3, 7, 8, 9]


def test_handles_the_second_list_coming_entirely_first() -> None:
    """Puts the second list ahead of the first when all its values are smaller.

    The result's head comes from `second`, so a solution that assumes the
    answer starts at `first` -- which a merge written without a dummy node
    often does -- returns a list missing its own front.
    """
    first, _ = build([10, 20])
    second, _ = build([1, 2])

    assert walk(merge_two_lists(first, second)) == [1, 2, 10, 20]


def test_attaches_the_whole_remainder() -> None:
    """Keeps every node when one list is far longer than the other.

    Stopping at the shorter list's end and forgetting the tail splice loses
    everything past it -- a bug the equal-length tests above cannot see.
    """
    first, _ = build([1])
    second, _ = build([2, 3, 4, 5, 6, 7])

    assert walk(merge_two_lists(first, second)) == [1, 2, 3, 4, 5, 6, 7]


def test_keeps_duplicate_values_across_both_lists() -> None:
    """Keeps every duplicate rather than collapsing them."""
    first, _ = build([1, 2, 2])
    second, _ = build([2, 2, 3])

    assert walk(merge_two_lists(first, second)) == [1, 2, 2, 2, 2, 3]


def test_reuses_the_nodes_it_was_given() -> None:
    """Splices the original nodes rather than building new ones.

    A solution that reads both lists into one Python list, sorts it and builds
    a fresh chain returns the right values and passes every test above. This
    one asserts object identity.
    """
    first, first_nodes = build([1, 3])
    second, second_nodes = build([2, 4])

    result = merge_two_lists(first, second)

    assert result is first_nodes[0]
    assert result.next is second_nodes[0]
    assert walk(result) == [1, 2, 3, 4]


def test_handles_negative_values() -> None:
    """Merges correctly across negative and positive values."""
    first, _ = build([-5, -1, 4])
    second, _ = build([-3, 0])

    assert walk(merge_two_lists(first, second)) == [-5, -3, -1, 0, 4]
