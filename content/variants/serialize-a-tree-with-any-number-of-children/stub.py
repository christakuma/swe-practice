"""Your solution goes here. The tests import from this module."""

from __future__ import annotations


class Node:
    """A tree node with any number of children, in order."""

    def __init__(self, value: int, children: list[Node] | None = None) -> None:
        self.value = value
        self.children: list[Node] = children if children is not None else []


def serialize(root: Node | None) -> str:
    """Pack a tree into a string.

    Args:
        root: the root of the tree, or None.

    Returns:
        A string from which `deserialize` recovers an identical tree.
    """
    raise NotImplementedError


def deserialize(data: str) -> Node | None:
    """Unpack a string produced by `serialize`.

    Args:
        data: the output of `serialize`.

    Returns:
        A tree identical in shape, child order and values to the original.
    """
    raise NotImplementedError
