"""Your solution goes here.

The tests import both `ListNode` and `sort_list` from this module, so keep
the class as it is -- it is how the tests build the lists they hand you.
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


def sort_list(head: ListNode | None) -> ListNode | None:
    """Sort the list into ascending order by relinking its nodes.

    Args:
        head: the first node of the list, or None for an empty list.

    Returns:
        The head of the sorted list, made of the same nodes. Nodes with
        equal values keep their original order.
    """
    raise NotImplementedError
