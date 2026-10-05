"""Your solution goes here.

The tests import both `ListNode` and `reorder_list` from this module, so keep
the class as it is -- it is how the tests build the lists they hand you.
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


def reorder_list(head: ListNode | None) -> None:
    """Reorder the list in place to alternate front, back, front, back.

    Args:
        head: the first node of the list. It stays the first node, which is why
            nothing is returned -- the caller's handle must remain valid.

    Returns:
        Nothing. The reordering is done by relinking the nodes in place.
    """
    raise NotImplementedError
