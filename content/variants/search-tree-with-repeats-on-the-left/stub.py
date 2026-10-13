"""Your solution goes here.

The tests import the node class from this module too, so keep it as it is --
it is how the tests build what they hand you.
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
    """Whether the tree is a search tree that allows repeats on the left.

    Every value in a node's left subtree must be less than or equal to the
    node's value, and every value in its right subtree strictly greater.

    Args:
        root: the root of the tree, or None for an empty tree.

    Returns:
        True if every node satisfies the rule.
    """
    raise NotImplementedError
