"""Your solution goes here.

The tests import both `TreeNode` and `lowest_common_ancestor` from this
module, so keep the class as it is -- it is how the tests build trees to hand
you.
"""

from __future__ import annotations


class TreeNode:
    """A binary tree node that knows its parent."""

    def __init__(self, value: int, parent: TreeNode | None = None) -> None:
        self.value = value
        self.parent = parent
        self.left: TreeNode | None = None
        self.right: TreeNode | None = None


def lowest_common_ancestor(first: TreeNode, second: TreeNode) -> TreeNode:
    """Return the deepest node with both given nodes at or below it.

    Args:
        first: a node of the tree.
        second: a node of the same tree, possibly the same node.

    Returns:
        The lowest common ancestor, as a node. A node is an ancestor of
        itself.
    """
    raise NotImplementedError
