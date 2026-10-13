"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import ListNode, reorder_list


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


def test_groups_an_odd_length_list() -> None:
    """Puts positions 1, 3, 5 ahead of positions 2, 4."""
    head = linked([1, 2, 3, 4, 5])

    reorder_list(head)

    assert values_of(head) == [1, 3, 5, 2, 4]


def test_groups_an_even_length_list() -> None:
    """Puts positions 1, 3 ahead of positions 2, 4."""
    head = linked([1, 2, 3, 4])

    reorder_list(head)

    assert values_of(head) == [1, 3, 2, 4]


def test_goes_by_position_not_by_value() -> None:
    """Groups by where a node is, not by whether its value is odd."""
    head = linked([2, 1, 3, 5, 6, 4])

    reorder_list(head)

    assert values_of(head) == [2, 3, 6, 1, 5, 4]


def test_leaves_short_lists_alone() -> None:
    """Leaves lists of nought, one and two nodes as they are."""
    assert reorder_list(None) is None
    for values in ([7], [7, 8]):
        head = linked(values)
        assert reorder_list(head) is None
        assert values_of(head) == values


def test_agrees_with_slicing_at_every_length() -> None:
    """Matches odd-then-even slicing for every length up to twenty."""
    for length in range(1, 21):
        values = list(range(length))
        head = linked(values)
        reorder_list(head)
        assert values_of(head) == values[0::2] + values[1::2], length


def test_relinks_the_original_nodes() -> None:
    """Moves the nodes themselves rather than copying values between them."""
    head = linked([10, 20, 30, 40, 50])
    originals = []
    node = head
    while node is not None:
        originals.append(node)
        node = node.next

    reorder_list(head)

    assert [node.value for node in originals] == [10, 20, 30, 40, 50]
    assert originals[0].next is originals[2]
    assert originals[4].next is originals[1]


def test_reorders_a_long_list() -> None:
    """Reorders twenty thousand nodes without recursing."""
    size = 20_000
    head = linked(list(range(size)))

    reorder_list(head)

    assert values_of(head) == list(range(0, size, 2)) + list(range(1, size, 2))
