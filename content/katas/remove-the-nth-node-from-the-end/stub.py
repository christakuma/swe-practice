"""Your solution goes here.

The tests import both `ListNode` and `remove_nth_from_end` from this module,
so keep the class as it is -- it is how the tests build the lists they hand
you.
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


def remove_nth_from_end(head: ListNode | None, n: int) -> ListNode | None:
    """Unlink the nth node from the end and return the head.

    Args:
        head: the first node of the list.
        n: how far from the end the doomed node is. 1 is the last node. Never
            larger than the length of the list.

    Returns:
        The head of the list with that node unlinked, which is a different node
        from `head` when the head itself was removed. None when the list had
        one node.
    """
    raise NotImplementedError
