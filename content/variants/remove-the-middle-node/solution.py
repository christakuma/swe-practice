"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class ListNode:
    """A singly linked list node.

    The attribute is `next`, which is what traversal code expects to write;
    the constructor parameter cannot be, because it would shadow a builtin.
    """

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next = next_node


def remove_middle(head: ListNode | None) -> ListNode | None:
    """Unlink the middle node and return the head.

    A slow pointer and a fast one moving at twice the speed. The fast pointer
    starts two nodes ahead, so when it falls off the end the slow one is on
    the node *before* the middle -- which is the node whose link has to
    change. One pass, and the length is never known.
    """
    if head is None or head.next is None:
        return None
    slow = head
    fast = head.next.next
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
    slow.next = slow.next.next
    return head
