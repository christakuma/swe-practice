"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class ListNode:
    """A singly linked list node."""

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next_node = next_node


def _reverse(head: ListNode | None) -> ListNode | None:
    """Reverse a list in place and return its new head."""
    previous = None
    while head is not None:
        head.next_node, previous, head = previous, head, head.next_node
    return previous


def is_palindrome(head: ListNode | None) -> bool:
    """Return whether the list's values read the same in both directions.

    Three borrowed steps. A slow and a fast pointer find the middle. The half
    from there on is reversed in place, giving a second list that reads the
    back of the original from the end inwards. Then the two are walked in
    step and compared.

    `slow` stops at the middle node of an odd list and the first node of the
    second half of an even one, so the reversed half is never the longer one
    and the comparison runs until *it* ends. The first half's last node still
    points into the reversed half's tail, which is harmless -- the loop stops
    before following it.

    The repair is not optional and is not on a branch: the answer is computed
    in full, the second half is reversed back, and only then returned.
    """
    slow = fast = head
    while fast is not None and fast.next_node is not None:
        slow = slow.next_node
        fast = fast.next_node.next_node

    tail = _reverse(slow)
    matches = True
    front, back = head, tail
    while back is not None:
        if front.value != back.value:
            matches = False
            break
        front, back = front.next_node, back.next_node
    _reverse(tail)
    return matches
