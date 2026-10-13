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


def merge_two_lists(
    first: ListNode | None,
    second: ListNode | None,
) -> ListNode | None:
    """Merge two ascending lists into one descending list.

    The ordinary merge picks the smaller front node; this one does too, and
    then pushes it onto the *front* of the result instead of the back. The
    smallest value goes in first and is pushed further down by everything
    that follows, so the list comes out largest first in a single pass.
    """
    head = None
    while first is not None or second is not None:
        if second is None or (first is not None and first.value <= second.value):
            taken, first = first, first.next
        else:
            taken, second = second, second.next
        taken.next = head
        head = taken
    return head
