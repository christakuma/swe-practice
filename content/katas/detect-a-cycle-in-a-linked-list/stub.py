"""Your solution goes here.

The tests import both `ListNode` and `has_cycle` from this module, so keep the
class as it is -- it is how the tests build lists to hand you.
"""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def has_cycle(head: ListNode | None) -> bool:
    """Whether following `next_node` from `head` ever revisits a node.

    Args:
        head: the first node, or None for an empty list.

    Returns:
        True if the list loops back on itself.
    """
    raise NotImplementedError
