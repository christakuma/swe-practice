"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise

from solution import ListNode, reverse_list


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


def test_reverses_a_short_list() -> None:
    """Returns the values in reverse order."""
    head, _ = build([1, 2, 3, 4])

    assert walk(reverse_list(head)) == [4, 3, 2, 1]


def test_handles_an_empty_list() -> None:
    """Returns an empty list for an empty list."""
    assert reverse_list(None) is None


def test_handles_a_single_node() -> None:
    """Returns a one-node list unchanged."""
    head, _ = build([7])

    assert walk(reverse_list(head)) == [7]


def test_handles_two_nodes() -> None:
    """Swaps a two-node list."""
    head, _ = build([1, 2])

    assert walk(reverse_list(head)) == [2, 1]


def test_reuses_the_nodes_it_was_given() -> None:
    """Relinks the original nodes rather than building new ones.

    A solution that reads the values into a list, reverses that and builds a
    fresh chain returns the right values and passes every test above. This one
    asserts object identity: the node returned must *be* the original tail.
    """
    head, nodes = build([1, 2, 3, 4])

    result = reverse_list(head)

    assert result is nodes[-1]
    assert walk(result) == [4, 3, 2, 1]


def test_leaves_the_old_head_as_a_terminated_tail() -> None:
    """Ends the reversed list at the original head.

    Forgetting to seed the trailing pointer as None leaves the old head still
    pointing at its old successor, which closes the list into a cycle. The
    values come out right for a few steps and then never stop.
    """
    head, nodes = build([1, 2, 3])
    original_head = nodes[0]

    reverse_list(head)

    assert original_head.next is None


def test_does_not_leave_a_cycle() -> None:
    """Returns a list that terminates."""
    head, _ = build([1, 2, 3, 4, 5])

    assert walk(reverse_list(head), limit=10) == [5, 4, 3, 2, 1]


def test_handles_duplicate_and_negative_values() -> None:
    """Reverses by position, not by value."""
    head, _ = build([3, -1, 3, 0, -1])

    assert walk(reverse_list(head)) == [-1, 0, 3, -1, 3]


def test_reverses_a_list_too_long_to_recurse_over() -> None:
    """Reverses a list far longer than the recursion limit allows.

    Thirty thousand nodes. The declared space bound is O(1), and a recursive
    reversal costs a stack frame per node -- so this is where that claim is
    actually tested rather than merely asserted on the page.
    """
    head, _ = build(list(range(30_000)))

    assert walk(reverse_list(head)) == list(range(29_999, -1, -1))
