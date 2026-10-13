"""Your solution goes here.

The tests import both `ListNode` and `reverse_in_groups` from this module, so
keep the class as it is -- it is how the tests build lists to hand you.
"""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def reverse_in_groups(head: ListNode | None, k: int) -> ListNode | None:
    """Reverse the list `k` nodes at a time.

    Args:
        head: the first node, or None for an empty list.
        k: the group size, at least 1.

    Returns:
        The head of the list with each full group of `k` nodes reversed. A
        final group of fewer than `k` nodes keeps its order.
    """
    raise NotImplementedError
