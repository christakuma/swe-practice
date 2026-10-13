"""Your solution goes here.

The tests import both `ListNode` and `rotate` from this module, so keep the
class as it is -- it is how the tests build lists to hand you.
"""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def rotate(head: ListNode | None, k: int) -> ListNode | None:
    """Move the last `k` nodes of the list to its front.

    Args:
        head: the first node, or None for an empty list.
        k: how many places to rotate to the right. Never negative; may
            exceed the length of the list.

    Returns:
        The head of the rotated list, made of the same nodes.
    """
    raise NotImplementedError
