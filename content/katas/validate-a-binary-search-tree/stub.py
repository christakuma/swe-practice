"""Your solution goes here.

The tests import both `TreeNode` and `is_search_tree` from this module, so keep
the class as it is -- it is how the tests build trees to hand you.
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


def is_search_tree(root: TreeNode | None) -> bool:
    """Whether the tree satisfies the binary search tree property.

    Every value in a node's left subtree must be strictly less than the node's
    value, and every value in its right subtree strictly greater.

    Args:
        root: the root of the tree, or None for an empty tree.

    Returns:
        True if the whole tree is a valid binary search tree.
    """
    raise NotImplementedError
