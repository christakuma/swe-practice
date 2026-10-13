"""Your solution goes here.

The tests import both `ListNode` and `is_palindrome` from this module, so keep
the class as it is -- it is how the tests build lists to hand you.
"""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def is_palindrome(head: ListNode | None) -> bool:
    """Return whether the list's values read the same in both directions.

    Args:
        head: the first node, or None for an empty list. The list must be
            left exactly as it was found.

    Returns:
        True if the sequence of values equals its own reverse.
    """
    raise NotImplementedError
