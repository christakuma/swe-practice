"""Your solution goes here.

The tests import both `TreeNode` and `rebuild` from this module, so keep the
class as it is -- it is what the tests inspect.
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


def rebuild(preorder: list[int]) -> TreeNode | None:
    """Rebuild a binary search tree from its pre-order traversal.

    Args:
        preorder: the values in pre-order: node, left subtree, right subtree.
            All distinct. Must not be modified.

    Returns:
        The root of the search tree whose pre-order traversal is `preorder`,
        or None if the list is empty.
    """
    raise NotImplementedError
