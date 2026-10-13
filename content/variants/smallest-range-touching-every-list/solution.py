"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

import heapq


class ListNode:
    """A singly linked list node.

    The attribute is `next`, which is what traversal code expects to write;
    the constructor parameter cannot be, because it would shadow a builtin.
    """

    def __init__(self, value: int, next_node: ListNode | None = None) -> None:
        self.value = value
        self.next = next_node


def smallest_range(lists: list[ListNode | None]) -> tuple[int, int] | None:
    """Return the narrowest range holding a value from every list.

    The k-way merge holds one node from each list in a heap. Read as a set,
    those k nodes are one value from every list, so the span from the least
    to the greatest of them is a range that touches every list -- and the
    tightest one whose low end is that least value, because each list is
    represented by its smallest value not yet passed.

    So the merge, run without building anything, visits the best range for
    every possible low end in ascending order. The answer is the narrowest
    seen.

    The heap yields the least; the greatest is tracked by hand, and only a
    push can raise it. The comparison is strict so that, among ranges of the
    same width, the first one met -- the one with the smallest low end --
    is kept.

    The loop ends when the list holding the least value is exhausted. Any
    later range would have to start above that list's last value and so
    could not include it.

    The middle entry of each heap item is the list's index, there only to
    break ties between equal values before the comparison reaches the nodes,
    which do not compare.
    """
    if not lists or any(head is None for head in lists):
        return None

    heap = [
        (head.value, index, head)
        for index, head in enumerate(lists)
        if head is not None
    ]
    heapq.heapify(heap)
    highest = max(value for value, _, _ in heap)

    best = (heap[0][0], highest)
    while True:
        lowest, index, node = heap[0]
        if highest - lowest < best[1] - best[0]:
            best = (lowest, highest)
        if node.next is None:
            return best
        following = node.next
        highest = max(highest, following.value)
        heapq.heapreplace(heap, (following.value, index, following))
