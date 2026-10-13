"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import ListNode, remove_middle


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


def test_removes_the_middle_of_an_odd_list() -> None:
    """Removes the centre node of five."""
    assert values_of(remove_middle(linked([1, 2, 3, 4, 5]))) == [1, 2, 4, 5]


def test_removes_the_second_middle_of_an_even_list() -> None:
    """Removes the second of the two centre nodes of four."""
    assert values_of(remove_middle(linked([1, 2, 3, 4]))) == [1, 2, 4]


def test_handles_the_shortest_lists() -> None:
    """Empties a one-node list and keeps the first of two."""
    assert remove_middle(linked([1])) is None
    assert values_of(remove_middle(linked([1, 2]))) == [1]
    assert values_of(remove_middle(linked([1, 2, 3]))) == [1, 3]


def test_removes_index_n_over_two_at_every_length() -> None:
    """Removes the node at index n // 2 for every length up to thirty."""
    for length in range(1, 31):
        values = list(range(length))
        expected = values[: length // 2] + values[length // 2 + 1 :]
        assert values_of(remove_middle(linked(values))) == expected, length


def test_removes_by_position_not_by_value() -> None:
    """Removes the centre node even when every value is the same."""
    assert values_of(remove_middle(linked([7, 7, 7]))) == [7, 7]


def test_unlinks_from_the_original_chain() -> None:
    """Returns the original head and the original nodes."""
    head = linked([1, 2, 3, 4, 5])
    second = head.next if head is not None else None

    result = remove_middle(head)

    assert result is head
    assert result is not None
    assert result.next is second


def test_handles_a_long_list() -> None:
    """Removes the middle of a hundred thousand nodes without recursing."""
    size = 100_000
    expected = list(range(size // 2)) + list(range(size // 2 + 1, size))

    assert values_of(remove_middle(linked(list(range(size))))) == expected
