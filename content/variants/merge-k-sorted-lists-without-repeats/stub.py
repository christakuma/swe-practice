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


def merge_k_lists(lists: list[ListNode | None]) -> ListNode | None:
    """Merge k sorted lists into one sorted list with no repeated value.

    Args:
        lists: the heads of the sorted lists. The outer list may be empty,
            and any entry may be None.

    Returns:
        The head of an ascending list holding each distinct value once,
        reusing nodes passed in. None when there are no nodes at all.
    """
    raise NotImplementedError
