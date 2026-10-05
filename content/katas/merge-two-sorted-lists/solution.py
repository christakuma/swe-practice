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
    """Merge two sorted lists into one sorted list.

    Both inputs are sorted, which means the smallest node not yet used is
    always at the front of one list or the other -- so the merge never
    searches, it only compares two candidates.

    The dummy node is the point of the exercise. Without it the first append
    is a special case (there is no tail to append to yet), and that special
    case has to be re-tested on every iteration or hoisted into a branch
    before the loop. One throwaway node deletes it: `tail` always exists, so
    the loop body has exactly one shape.

    `<=` rather than `<` keeps equal values in their original relative order.
    The prompt does not require it, but a merge that is stable costs nothing
    here and is the behaviour every sort built on this one depends on.

    The final attach is the other half of why this is O(1) space: when one list
    is exhausted the other is already sorted and already linked, so the
    remainder is spliced on in a single write instead of copied node by node.
    """
    dummy = ListNode(0)
    tail = dummy
    while first is not None and second is not None:
        if first.value <= second.value:
            tail.next = first
            first = first.next
        else:
            tail.next = second
            second = second.next
        tail = tail.next
    tail.next = first if first is not None else second
    return dummy.next
