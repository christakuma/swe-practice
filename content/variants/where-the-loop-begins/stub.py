"""Your solution goes here.

The tests import both `ListNode` and `cycle_start` from this module, so keep
the class as it is -- it is how the tests build lists to hand you.
"""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def cycle_start(head: ListNode | None) -> ListNode | None:
    """Return the node at which the list's cycle begins.

    Args:
        head: the first node, or None for an empty list.

    Returns:
        The first node that following `next_node` from `head` reaches twice,
        or None if the list ends.
    """
    raise NotImplementedError
