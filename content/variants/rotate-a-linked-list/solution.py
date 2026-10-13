"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def rotate(head: ListNode | None, k: int) -> ListNode | None:
    """Move the last `k` nodes of the list to its front.

    One walk to the tail measures the list, and while standing there the tail
    is joined to the head. On a ring, "rotate" has no moving parts: the nodes
    are already in the right cyclic order, and all that remains is to choose
    where the ring is opened.

    The new tail is the node `length - k % length` steps on from the old
    tail. The modulus is what makes a `k` of a thousand million as cheap as a
    `k` of two; without it the walk would lap the ring that many times.
    """
    if head is None:
        return None
    length = 1
    tail = head
    while tail.next_node is not None:
        tail = tail.next_node
        length += 1

    tail.next_node = head
    for _ in range(length - k % length):
        tail = tail.next_node
    new_head = tail.next_node
    tail.next_node = None
    return new_head
