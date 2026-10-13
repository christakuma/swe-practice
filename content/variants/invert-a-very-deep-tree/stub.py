"""Your solution goes here.

The tests import both `TreeNode` and `invert` from this module, so keep the
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


def invert(root: TreeNode | None) -> TreeNode | None:
    """Mirror the tree in place and return its root.

    Args:
        root: the root of the tree, or None for an empty tree. The tree may
            be far deeper than Python's recursion limit.

    Returns:
        The same root node, with every node's left and right children
        swapped.
    """
    raise NotImplementedError
