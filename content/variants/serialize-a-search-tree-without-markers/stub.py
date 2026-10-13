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
    """Turn a binary search tree into a string of its values.

    Args:
        root: the root of a search tree with distinct values, or None.

    Returns:
        The values as decimal integers joined by commas, one per node and
        nothing else. The empty string for an empty tree.
    """
    raise NotImplementedError


def deserialize(data: str) -> TreeNode | None:
    """Rebuild the tree that `serialize` was given.

    Args:
        data: the output of `serialize`.

    Returns:
        A tree with the same values in the same shape.
    """
    raise NotImplementedError
