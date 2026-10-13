"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class Node:
    """A list node with a successor and a second pointer to any node."""

    def __init__(
        self,
        value: int,
        next_node: Node | None = None,
        random: Node | None = None,
    ) -> None:
        self.value = value
        self.next = next_node
        self.random = random


def copy_list(head: Node | None) -> Node | None:
    """Deep-copy a list whose nodes carry a random pointer.

    Two passes over the original. The first makes a bare copy of every node
    and records which copy belongs to which original. Only then are the
    pointers set, by looking each target up -- at which point every target
    already has a copy, whichever direction the pointer runs.

    `None` is put in the dict as its own copy, which removes the two `if`s
    that would otherwise guard a missing `next` or `random`.
    """
    copies: dict[Node | None, Node | None] = {None: None}
    node = head
    while node is not None:
        copies[node] = Node(node.value)
        node = node.next

    node = head
    while node is not None:
        copy = copies[node]
        if copy is not None:
            copy.next = copies[node.next]
            copy.random = copies[node.random]
        node = node.next
    return copies[head]
