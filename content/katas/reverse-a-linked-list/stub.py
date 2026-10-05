"""Your solution goes here.

The tests import both `ListNode` and `reverse_list` from this module, so keep
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


def reverse_list(head: ListNode | None) -> ListNode | None:
    """Reverse the list in place and return the new head.

    Args:
        head: the first node, or None for an empty list.

    Returns:
        The last node of the original list, now the head. None for an empty
        list. The returned chain must reuse the nodes passed in.
    """
    raise NotImplementedError
