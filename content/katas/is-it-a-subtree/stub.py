"""Your solution goes here.

The tests import both `TreeNode` and `is_subtree` from this module, so keep the
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


def is_subtree(tree: TreeNode | None, candidate: TreeNode | None) -> bool:
    """Return whether `candidate` appears in `tree` as a complete subtree.

    Args:
        tree: the tree to search.
        candidate: the shape to look for. None is a subtree of anything.

    Returns:
        True if some node of `tree` roots a subtree identical in shape and
        values to `candidate`.
    """
    raise NotImplementedError
