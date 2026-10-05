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


def merge_k_lists(lists: list[ListNode | None]) -> ListNode | None:
    """Merge k sorted lists into one sorted list.

    The two-list merge compares two front nodes. With k lists the same step is
    "find the smallest of k front nodes", and answering that by scanning costs
    O(k) per output node -- O(k * kn) overall, the slow answer the prompt rules
    out. A min-heap answers it in O(log k), and that one substitution is the
    whole kata.

    The heap holds **one entry per list, not one per node**: the current front
    of each. Pop the smallest, emit it, push its successor. So the heap never
    exceeds k entries, which is where the O(k) space bound comes from -- a
    solution that pushes every node up front sorts correctly and spends O(kn)
    space to do it.

    The list index is not decoration. `heapq` compares the tuples it is handed,
    and a tie in the first element sends it to the second -- which would be a
    ListNode, and ListNodes are not orderable, so two equal values would raise
    TypeError. Keeping the originating list's index there breaks every tie
    before a node is ever compared. Because the heap holds at most one entry
    per list, those indices are distinct at all times, so the tie *always*
    resolves and it resolves in favour of the earlier list -- which makes the
    merge stable, exactly as `<=` does in the two-list version.

    The dummy node earns its place for the same reason as in the two-list
    merge: the first append has no tail to append to, and a sentinel deletes
    that special case rather than branching on it n times.

    No final `tail.next = None` is needed, and the reason is worth seeing: the
    last node emitted is necessarily one whose `next` was already None. Had it
    had a successor, that successor would have been pushed and the loop would
    have run again to emit it.
    """
    heap: list[tuple[int, int, ListNode]] = [
        (head.value, index, head)
        for index, head in enumerate(lists)
        if head is not None
    ]
    heapq.heapify(heap)

    dummy = ListNode(0)
    tail = dummy
    while heap:
        _, index, node = heapq.heappop(heap)
        tail.next = node
        tail = node
        if node.next is not None:
            heapq.heappush(heap, (node.next.value, index, node.next))
    return dummy.next
