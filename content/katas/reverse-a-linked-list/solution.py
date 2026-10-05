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


def reverse_list(head: ListNode | None) -> ListNode | None:
    """Reverse the list in place and return the new head.

    Three names and one pass. Nothing moves: every node stays exactly where it
    was allocated, and the only writes are to `next` pointers.

    The ordering inside the loop is the whole exercise. `node.next` is the only
    route to the rest of the list, so `ahead` has to be read *before* that
    pointer is overwritten -- swap those two lines and the list is severed at
    the first node and the walk cannot continue.

    Seeding `behind` as None is what terminates the reversed list rather than
    leaving the original head pointing at its old successor, which would close
    the chain into a cycle. It also makes the empty list fall out for free: the
    loop never runs and None is already the right answer.
    """
    behind: ListNode | None = None
    node = head
    while node is not None:
        ahead = node.next
        node.next = behind
        behind = node
        node = ahead
    return behind
