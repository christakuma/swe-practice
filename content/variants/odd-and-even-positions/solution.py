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


def reorder_list(head: ListNode | None) -> None:
    """Reorder the list in place: odd positions first, then even positions.

    Two chains are threaded through the list at once. `odd` and `even` are
    their tails; each step links the odd tail to the node after the even
    tail and then the even tail to the node after that, so both advance
    together. The even chain's first node is remembered so the two can be
    joined when the walk runs out.
    """
    if head is None:
        return
    odd = head
    even_head = head.next
    even = even_head
    while even is not None and even.next is not None:
        odd.next = even.next
        odd = odd.next
        even.next = odd.next
        even = even.next
    odd.next = even_head
