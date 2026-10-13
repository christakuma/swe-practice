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


def reverse_between(head: ListNode | None, left: int, right: int) -> ListNode | None:
    """Reverse the nodes from position `left` to position `right`.

    A dummy node in front of the head means the range always has a
    predecessor, so a range starting at position 1 is not a special case.

    `before` is that predecessor and never moves. `tail` is the range's first
    node, which ends up as its last: each round lifts the node after `tail`
    out and reinserts it straight after `before`, so the range reverses one
    node at a time around a fixed anchor.
    """
    dummy = ListNode(0, head)
    before = dummy
    for _ in range(left - 1):
        before = before.next
    tail = before.next
    for _ in range(right - left):
        moving = tail.next
        tail.next = moving.next
        moving.next = before.next
        before.next = moving
    return dummy.next
