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


def remove_middle(head: ListNode | None) -> ListNode | None:
    """Unlink the middle node and return the head.

    Args:
        head: the first node of a list of at least one node.

    Returns:
        The head of the list without the node at index `n // 2`. None when
        the list had one node.
    """
    raise NotImplementedError
