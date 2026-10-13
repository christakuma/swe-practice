"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def cycle_start(head: ListNode | None) -> ListNode | None:
    """Return the node at which the list's cycle begins.

    Two phases. The first is the usual race: slow moves one node and fast
    two, and they meet only if there is a cycle. If slow has walked `a` nodes
    to the cycle and `b` more round it, fast has walked `2(a + b)`, and the
    difference `a + b` is a whole number of laps.

    That is the whole trick. From the meeting point, `a` more steps completes
    those laps and lands on the first node of the cycle -- and `a` steps is
    exactly how far the head is from it. So a second pointer from the head,
    moving in step, arrives there at the same moment.
    """
    slow = fast = head
    while fast is not None and fast.next_node is not None:
        slow = slow.next_node
        fast = fast.next_node.next_node
        if slow is fast:
            probe = head
            while probe is not slow:
                probe = probe.next_node
                slow = slow.next_node
            return probe
    return None
