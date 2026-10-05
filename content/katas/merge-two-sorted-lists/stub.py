"""Your solution goes here.

The tests import both `ListNode` and `merge_two_lists` from this module, so
keep the class as it is -- it is how the tests build the lists they hand you.
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


def merge_two_lists(
    first: ListNode | None,
    second: ListNode | None,
) -> ListNode | None:
    """Merge two sorted lists into one sorted list.

    Args:
        first: head of the first sorted list, or None if it is empty.
        second: head of the second sorted list, or None if it is empty.

    Returns:
        The head of a sorted list holding every node from both inputs, reusing
        the nodes passed in. None when both inputs are empty.
    """
    raise NotImplementedError
