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


def merge_two_lists(
    first: ListNode | None,
    second: ListNode | None,
) -> ListNode | None:
    """Merge two ascending lists into one descending list.

    Args:
        first: head of the first ascending list, or None if it is empty.
        second: head of the second ascending list, or None if it is empty.

    Returns:
        The head of a descending list holding every node from both inputs,
        reusing the nodes passed in. None when both are empty.
    """
    raise NotImplementedError
