"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def has_cycle(head: ListNode | None) -> bool:
    """Whether following `next_node` from `head` ever revisits a node.

    Floyd's two pointers: one step at a time, two steps at a time. If the list
    ends, the fast pointer falls off it. If it loops, the fast pointer is inside
    the loop gaining one position per step on the slow one, so it closes the gap
    and they meet -- which is the part worth being able to argue rather than
    recite. A gap that shrinks by exactly one per step cannot skip zero.

    Both guards in the `while` are needed: `fast` for a list of odd length, where
    the fast pointer lands exactly on the end, and `fast.next_node` for even, where
    it lands one short. Dropping either is an AttributeError on half of all
    acyclic inputs.

    A set of visited nodes is the obvious solution and is correct. It is O(n)
    space, and the only reason to prefer this one is that constant space is
    available for free -- which matters when the list is a disk structure, or
    when you are detecting a cycle in a sequence you cannot store (the same
    algorithm finds cycles in pseudorandom sequences, where there is no list at
    all).
    """
    slow = head
    fast = head
    while fast is not None and fast.next_node is not None:
        slow = slow.next_node
        fast = fast.next_node.next_node
        if slow is fast:
            return True
    return False
