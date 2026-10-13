"""Your solution goes here.

The tests import both `ListNode` and `smallest_range` from this module, so
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


def smallest_range(lists: list[ListNode | None]) -> tuple[int, int] | None:
    """Return the narrowest range holding a value from every list.

    Args:
        lists: the heads of the sorted lists. The outer list may be empty, and
            any entry may be None for an empty list. Not to be relinked.

    Returns:
        `(low, high)` with at least one value from every list between them,
        inclusive, and `high - low` as small as possible; the smallest `low`
        among ties. None when there are no lists or any list is empty.
    """
    raise NotImplementedError
