"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def cycle_length(head: ListNode | None) -> int:
    """Return the number of nodes in the list's cycle.

    Two phases. The first is the detection walk unchanged: a slow pointer and
    a fast one, which meet if and only if there is a cycle. Where they meet
    is somewhere inside it, and that is all the second phase needs -- a node
    known to be on the cycle. From there one pointer walks round until it is
    back where it started, counting.

    The steps taken in the first phase are not the answer. They are a
    multiple of the cycle's length, and a long tail makes the multiple more
    than one.
    """
    slow = fast = head
    while fast is not None and fast.next_node is not None:
        slow = slow.next_node
        fast = fast.next_node.next_node
        if slow is fast:
            break
    else:
        return 0

    length = 1
    walker = slow.next_node
    while walker is not slow:
        walker = walker.next_node
        length += 1
    return length
