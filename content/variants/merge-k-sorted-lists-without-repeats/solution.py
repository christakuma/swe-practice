"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

import heapq


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

    The standard heap merge, with one test before a node is linked in: is its
    value the one already at the tail? Equal values leave the heap
    consecutively, so that comparison catches every repeat.

    Two details keep it correct. A skipped node's successor is still pushed,
    or the rest of its list is lost. And the final `tail.next = None` is not
    decoration: the last node kept may still be linked to a duplicate that
    was skipped after it.
    """
    heap = [
        (node.value, index, node)
        for index, node in enumerate(lists)
        if node is not None
    ]
    heapq.heapify(heap)
    dummy = ListNode(0)
    tail = dummy
    while heap:
        value, index, node = heapq.heappop(heap)
        if node.next is not None:
            heapq.heappush(heap, (node.next.value, index, node.next))
        if tail is dummy or tail.value != value:
            tail.next = node
            tail = node
    tail.next = None
    return dummy.next
