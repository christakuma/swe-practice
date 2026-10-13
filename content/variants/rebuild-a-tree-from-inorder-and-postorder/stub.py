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


def rebuild(inorder: list[int], postorder: list[int]) -> TreeNode | None:
    """Rebuild the tree from its in-order and post-order traversals.

    Args:
        inorder: the values in in-order (left subtree, root, right subtree).
        postorder: the same values in post-order (left subtree, right
            subtree, root). All values are distinct.

    Returns:
        The root of the reconstructed tree, or None for empty input.
    """
    raise NotImplementedError
