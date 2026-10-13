"""Your solution goes here.

The tests import both `TreeNode` and `min_depth` from this module, so keep the
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


def min_depth(root: TreeNode | None) -> int:
    """Return the number of nodes on the shortest path from the root to a leaf.

    Args:
        root: the root of the tree, or None for an empty tree.

    Returns:
        The depth of the shallowest leaf, counted in nodes: 0 for an empty
        tree, 1 for a single node. A leaf is a node with no children.
    """
    raise NotImplementedError
