"""Your solution goes here.

The tests import both `ListNode` and `cycle_length` from this module, so keep
the class as it is -- it is how the tests build lists to hand you.
"""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def cycle_length(head: ListNode | None) -> int:
    """Return the number of nodes in the list's cycle.

    Args:
        head: the first node, or None for an empty list.

    Returns:
        How many distinct nodes are visited again and again when following
        `next_node` from `head`, or 0 if the list ends.
    """
    raise NotImplementedError
