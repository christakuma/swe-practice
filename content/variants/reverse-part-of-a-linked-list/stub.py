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


def reverse_between(head: ListNode | None, left: int, right: int) -> ListNode | None:
    """Reverse the nodes from position `left` to position `right`.

    Args:
        head: the first node of the list.
        left: the first position to reverse, counting from 1.
        right: the last position to reverse. Never before `left` and never
            past the end of the list.

    Returns:
        The head of the list, which is a different node from `head` when
        `left` is 1. The chain reuses the nodes passed in.
    """
    raise NotImplementedError
