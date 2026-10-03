"""Your solution goes here.

The tests import both `TreeNode` and `level_order` from this module, so keep the
class as it is -- it is how the tests build trees to hand you.
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


def level_order(root: TreeNode | None) -> list[list[int]]:
    """Return the values level by level, top to bottom, left to right.

    Args:
        root: the root of the tree, or None for an empty tree.

    Returns:
        One list per level, starting with the root's level. Empty for an empty
        tree.
    """
    raise NotImplementedError
