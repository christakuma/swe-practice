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


def is_subtree(tree: TreeNode | None, candidate: TreeNode | None) -> bool:
    """Return whether `candidate` fits over part of `tree`, from some node down.

    Args:
        tree: the tree to search.
        candidate: the shape to look for. None is contained in anything.

    Returns:
        True if some node of `tree` matches `candidate`'s root and every
        node of `candidate` has a same-valued node in the same position
        below it. The tree may have further nodes the candidate lacks.
    """
    raise NotImplementedError
