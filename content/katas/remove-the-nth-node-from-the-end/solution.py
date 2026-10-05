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


def remove_nth_from_end(head: ListNode | None, n: int) -> ListNode | None:
    """Unlink the nth node from the end and return the head.

    "The nth node from the end" cannot be counted directly, because a singly
    linked list offers no way back. The trick is to stop trying: hold two
    pointers a fixed n nodes apart and move them in step, and the moment the
    front one reaches the last node the back one is standing exactly where it
    needs to be. The gap does the counting, which is what makes this one pass
    instead of two.

    Two details make it come out right rather than nearly right.

    Both pointers start at the *dummy*, not at the head. Unlinking a node
    requires the node before it -- there is no route backwards -- so `behind`
    has to land one short of the target. Starting at the dummy and advancing
    `front` n times sets up precisely that offset.

    And the dummy is what stops "remove the head" from being a second shape of
    the same operation. When n equals the length the doomed node *is* the head,
    which has no predecessor; the dummy lends it one. `dummy.next` is then the
    right answer in every case, including the one-node list, where it is None.

    `front` is never None here: the prompt guarantees n is at most the length,
    so advancing n times from the dummy lands on a real node at worst the last.
    """
    dummy = ListNode(0, head)
    front = dummy
    behind = dummy
    for _ in range(n):
        front = front.next
    while front.next is not None:
        front = front.next
        behind = behind.next
    behind.next = behind.next.next
    return dummy.next
