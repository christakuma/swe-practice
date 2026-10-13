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


def sort_list(head: ListNode | None) -> ListNode | None:
    """Sort the list into ascending order by relinking its nodes.

    Merge sort, which is the sort a linked list is good at: it needs only to
    walk forward and to splice, and never to jump to a position.

    The halving is the reorder problem's first step. `fast` starts one node
    ahead of `slow`, so that for two nodes `slow` stops on the first and the
    cut leaves one node each side. Starting them level would leave `slow` on
    the second, the second half empty, and the first half the whole list
    again -- recursion with no end.

    The cut has to be made, not just found: `slow.next = None`. Without it
    the first half still runs on into the second.

    The recursion is on halves, so its depth is the logarithm of the length
    -- sixteen frames for fifty thousand nodes -- which is why recursing is
    safe here when recursing along a list's length is not.
    """
    if head is None or head.next is None:
        return head

    slow, fast = head, head.next
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next

    second = slow.next
    slow.next = None
    return _merge(sort_list(head), sort_list(second))


def _merge(first: ListNode | None, second: ListNode | None) -> ListNode | None:
    """Splice two sorted lists into one.

    The comparison is strict so that on a tie the node from `first` goes
    in. Everything in `first` came before everything in `second` in the
    original list, so that preference is the whole of what stability means.
    """
    dummy = tail = ListNode(0)
    while first is not None and second is not None:
        if second.value < first.value:
            tail.next, second = second, second.next
        else:
            tail.next, first = first, first.next
        tail = tail.next
    tail.next = first if first is not None else second
    return dummy.next
