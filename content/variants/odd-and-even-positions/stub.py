"""Your solution goes here.

The tests import the node class from this module too, so keep it as it is --
it is how the tests build what they hand you.
"""

from __future__ import annotations


class ListNode:
    """A singly linked list node.

    The attribute is `next`, which is what traversal code expects to write;
    the constructor parameter cannot be, because it would shadow a builtin.
    """

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next = next_node


def reorder_list(head: ListNode | None) -> None:
    """Reorder the list in place: odd positions first, then even positions.

    Args:
        head: the first node of the list. It stays the first node.

    Returns:
        Nothing. The reordering is done by relinking the nodes in place.
    """
    raise NotImplementedError
