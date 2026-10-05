"""Your solution goes here.

The tests import `TreeNode`, `serialize` and `deserialize` from this module,
so keep the class as it is -- it is how the tests build trees to hand you.
"""

from __future__ import annotations


class TreeNode:
    """A binary tree node."""

    def __init__(
        self,
        value: int,
        left: TreeNode | None = None,
        right: TreeNode | None = None,
    ) -> None:
        self.value = value
        self.left = left
        self.right = right


def serialize(root: TreeNode | None) -> str:
    """Pack a binary tree into a string.

    Args:
        root: the root of an arbitrary binary tree, or None.

    Returns:
        A string from which `deserialize` recovers an identical tree.
    """
    raise NotImplementedError


def deserialize(data: str) -> TreeNode | None:
    """Unpack a string produced by `serialize`.

    Args:
        data: the output of `serialize`.

    Returns:
        A tree identical in shape and values to the one that was serialised.
    """
    raise NotImplementedError
