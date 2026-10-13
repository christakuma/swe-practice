"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def reverse_in_groups(head: ListNode | None, k: int) -> ListNode | None:
    """Reverse the list `k` nodes at a time.

    `before` is the node just ahead of the group being worked on -- a dummy
    for the first group, so that every group has one. Each round does three
    things in order.

    Look ahead `k` nodes from `before`. If the list ends first, the group is
    short and the work is finished.

    Reverse the group with the ordinary three-pointer loop, run exactly `k`
    times, starting with `previous` set to the node *after* the group. That
    choice does the back half of the stitching for free: the group's old
    first node, which ends up last, already points onward.

    Finish the stitching by pointing `before` at the group's new first node,
    and move `before` to the group's new last node.
    """
    dummy = ListNode(0, head)
    before = dummy
    while True:
        last = before
        for _ in range(k):
            last = last.next_node
            if last is None:
                return dummy.next_node

        first = before.next_node
        previous, node = last.next_node, first
        for _ in range(k):
            node.next_node, previous, node = previous, node, node.next_node
        before.next_node = previous
        before = first
