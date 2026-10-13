"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import ListNode, reverse_between


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
    """Every node in order."""
    found = []
    while head is not None:
        found.append(head)
        head = head.next
    return found


def test_reverses_a_stretch_in_the_middle() -> None:
    """Reverses positions 2 to 4 and leaves the ends in place."""
    head = linked([1, 2, 3, 4, 5])

    assert values_of(reverse_between(head, 2, 4)) == [1, 4, 3, 2, 5]


def test_reverses_from_the_head() -> None:
    """Returns the new first node when the range starts at position 1."""
    assert values_of(reverse_between(linked([1, 2, 3]), 1, 2)) == [2, 1, 3]


def test_reverses_up_to_the_tail() -> None:
    """Reverses a range that ends at the last node."""
    assert values_of(reverse_between(linked([1, 2, 3, 4]), 3, 4)) == [1, 2, 4, 3]


def test_reverses_the_whole_list() -> None:
    """Reverses everything when the range is the whole list."""
    assert values_of(reverse_between(linked([1, 2, 3, 4]), 1, 4)) == [4, 3, 2, 1]


def test_leaves_a_range_of_one_alone() -> None:
    """Changes nothing when left equals right."""
    assert values_of(reverse_between(linked([1, 2, 3]), 2, 2)) == [1, 2, 3]
    assert values_of(reverse_between(linked([7]), 1, 1)) == [7]


def test_agrees_with_slicing_for_every_range_of_every_short_list() -> None:
    """Matches a slice reversal for every range of every list up to nine nodes."""
    for length in range(1, 10):
        for left in range(1, length + 1):
            for right in range(left, length + 1):
                values = list(range(length))
                expected = (
                    values[: left - 1] + values[left - 1 : right][::-1] + values[right:]
                )
                result = reverse_between(linked(values), left, right)
                assert values_of(result) == expected, (length, left, right)


def test_relinks_the_original_nodes() -> None:
    """Returns the nodes it was given, each still holding its own value.

    A solution that swaps the values between nodes produces the right
    sequence of values and leaves every node where it was.
    """
    head = linked([10, 20, 30, 40, 50])
    originals = nodes_of(head)

    result = nodes_of(reverse_between(head, 2, 4))

    assert [node.value for node in originals] == [10, 20, 30, 40, 50]
    assert [originals.index(node) for node in result] == [0, 3, 2, 1, 4]


def test_reverses_a_long_list_without_recursing() -> None:
    """Reverses thirty thousand nodes, and a long stretch inside them."""
    size = 30_000

    assert values_of(reverse_between(linked(list(range(size))), 1, size)) == list(
        range(size - 1, -1, -1)
    )
    middle = values_of(reverse_between(linked(list(range(size))), 2, size - 1))
    assert middle == [0, *range(size - 2, 0, -1), size - 1]
