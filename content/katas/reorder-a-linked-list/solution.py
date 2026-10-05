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
    """Reorder the list in place to alternate front, back, front, back.

    Three operations you have already met, composed -- which is the reason this
    kata is worth doing even though none of its three steps is new:

    1. find the middle with a slow pointer and a fast one going twice as fast;
    2. reverse the second half, so the back of the list can be read forwards;
    3. weave the two halves together, taking one node from each in turn.

    The cut in step 1 is the part that bites. `slow.next = None` has to happen
    *before* the reverse, because otherwise the first half's tail still points
    into the second half -- and after the reverse that pointer aims at the
    second half's new tail, so the weave closes the list into a cycle. The
    values look right for a few steps and then never stop.

    `fast.next is not None and fast.next.next is not None` leaves `slow` on the
    last node of the first half for both parities: the first half gets the
    extra node on an odd length, so the second half is never longer. That is
    what lets the weave loop be driven by the second half running out.
    """
    if head is None or head.next is None:
        return

    slow = head
    fast = head
    while fast.next is not None and fast.next.next is not None:
        slow = slow.next
        fast = fast.next.next

    # Only now, with the midpoint known, is it safe to sever the halves.
    back = slow.next
    slow.next = None

    behind = None
    while back is not None:
        ahead = back.next
        back.next = behind
        behind = back
        back = ahead

    front = head
    while behind is not None:
        front_ahead = front.next
        behind_ahead = behind.next
        front.next = behind
        behind.next = front_ahead
        front = front_ahead
        behind = behind_ahead
