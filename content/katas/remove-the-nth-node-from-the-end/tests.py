"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise

from solution import ListNode, remove_nth_from_end


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


def test_removes_a_node_from_the_middle() -> None:
    """Removes the nth node counting from the end."""
    head, _ = build([1, 2, 3, 4, 5])

    assert walk(remove_nth_from_end(head, 2)) == [1, 2, 3, 5]


def test_removes_the_last_node() -> None:
    """Removes the final node when n is 1."""
    head, _ = build([1, 2, 3])

    assert walk(remove_nth_from_end(head, 1)) == [1, 2]


def test_removes_the_head() -> None:
    """Removes the first node when n equals the length.

    The head has no predecessor to unlink it from, so a solution written
    without a sentinel node either crashes here or returns the original head
    and drops nothing. Every other test in this file passes either way.
    """
    head, _ = build([1, 2, 3])

    assert walk(remove_nth_from_end(head, 3)) == [2, 3]


def test_empties_a_single_node_list() -> None:
    """Returns an empty list when the only node is removed."""
    head, _ = build([9])

    assert remove_nth_from_end(head, 1) is None


def test_removes_the_head_of_a_two_node_list() -> None:
    """Returns the second node when the head of a pair is removed."""
    head, nodes = build([1, 2])

    result = remove_nth_from_end(head, 2)

    assert result is nodes[1]
    assert walk(result) == [2]


def test_removes_the_tail_of_a_two_node_list() -> None:
    """Returns the first node alone when the tail of a pair is removed."""
    head, _ = build([1, 2])

    assert walk(remove_nth_from_end(head, 1)) == [1]


def test_terminates_the_list_after_removing_the_tail() -> None:
    """Leaves the new last node pointing at nothing.

    Unlinking the tail by advancing past it without writing the predecessor's
    pointer leaves that pointer dangling at the removed node, so the value
    comes back out on the next walk.
    """
    head, nodes = build([1, 2, 3])

    remove_nth_from_end(head, 1)

    assert nodes[1].next is None


def test_reuses_the_nodes_it_was_given() -> None:
    """Unlinks from the original chain rather than rebuilding it.

    A solution that reads the values into a list, deletes by index and builds a
    fresh chain returns the right values and passes every test above.
    """
    head, nodes = build([1, 2, 3, 4])

    result = remove_nth_from_end(head, 2)

    assert result is nodes[0]
    assert nodes[1].next is nodes[3]


def test_handles_a_list_of_duplicates() -> None:
    """Removes by position, not by value."""
    head, _ = build([7, 7, 7, 7])

    assert walk(remove_nth_from_end(head, 3)) == [7, 7, 7]


def test_handles_a_long_list_in_one_pass() -> None:
    """Removes from a long list without measuring it first."""
    head, _ = build(list(range(20_000)))

    result = walk(remove_nth_from_end(head, 10_000))

    assert len(result) == 19_999
    assert 10_000 not in result
