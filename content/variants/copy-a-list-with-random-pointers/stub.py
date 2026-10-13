"""Your solution goes here. The tests import from this module."""

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

    Args:
        head: the first node, or None for an empty list. Not to be modified.

    Returns:
        The head of a new list with the same values and the same pattern of
        `next` and `random` pointers, sharing no node with the original.
    """
    raise NotImplementedError
