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


def mirrored(root: TreeNode | None) -> TreeNode | None:
    """Return a new tree that is the mirror image of `root`.

    Args:
        root: the root of the tree, or None for an empty tree. Not to be
            modified.

    Returns:
        The root of a newly built tree with every node's children swapped.
        None for an empty tree. No node is shared with the original.
    """
    raise NotImplementedError
