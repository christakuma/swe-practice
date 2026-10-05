"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise

from solution import ListNode, reorder_list


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


def test_reorders_an_even_length_list() -> None:
    """Alternates front and back on an even-length list."""
    head, _ = build([1, 2, 3, 4])

    reorder_list(head)

    assert walk(head) == [1, 4, 2, 3]


def test_reorders_an_odd_length_list() -> None:
    """Alternates front and back on an odd-length list, middle node last."""
    head, _ = build([1, 2, 3, 4, 5])

    reorder_list(head)

    assert walk(head) == [1, 5, 2, 4, 3]


def test_handles_an_empty_list() -> None:
    """Leaves an empty list alone without raising."""
    assert reorder_list(None) is None


def test_handles_a_single_node() -> None:
    """Leaves a one-node list unchanged."""
    head, _ = build([1])

    reorder_list(head)

    assert walk(head) == [1]


def test_handles_two_nodes() -> None:
    """Leaves a two-node list unchanged -- it is already alternating."""
    head, _ = build([1, 2])

    reorder_list(head)

    assert walk(head) == [1, 2]


def test_handles_three_nodes() -> None:
    """Puts the middle node last on the shortest list that reorders."""
    head, _ = build([1, 2, 3])

    reorder_list(head)

    assert walk(head) == [1, 3, 2]


def test_terminates_rather_than_closing_a_cycle() -> None:
    """Leaves the list terminated.

    Reversing the back half without first severing it leaves the front half's
    tail pointing into the reversed chain, and the weave then closes the list
    into a loop. The values come out right for the first few steps, so only a
    length-bounded read can fail this instead of hanging.
    """
    head, _ = build([1, 2, 3, 4, 5, 6])

    reorder_list(head)

    assert walk(head, limit=20) == [1, 6, 2, 5, 3, 4]


def test_keeps_the_head_the_caller_holds() -> None:
    """Leaves the caller's head node first.

    Nothing is returned, so a solution that builds the right order onto a new
    head silently does nothing from the caller's point of view.
    """
    head, nodes = build([1, 2, 3, 4])

    reorder_list(head)

    assert head is nodes[0]
    assert nodes[0].next is nodes[3]


def test_reuses_the_nodes_it_was_given() -> None:
    """Relinks the original nodes rather than copying values between them.

    Collecting the nodes into a Python list, reading it from both ends and
    writing the values back into the original chain produces the right walk and
    is the wrong answer -- every node now holds somebody else's value.
    """
    head, nodes = build([10, 20, 30, 40])

    reorder_list(head)

    assert [node.value for node in nodes] == [10, 20, 30, 40]


def test_reorders_a_long_list() -> None:
    """Reorders a list long enough to rule out a quadratic walk."""
    size = 20_000
    head, _ = build(list(range(size)))

    reorder_list(head)
    result = walk(head)

    expected = []
    for index in range(size // 2):
        expected.extend((index, size - 1 - index))
    assert result == expected
