"""Reference solution. CI asserts this passes every test in `tests.py`."""

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


def best_path_sum(root: TreeNode) -> int:
    """Return the largest sum along any path from the root down to a leaf.

    One number comes back from each subtree: the best sum of a path from its
    root to one of its leaves. A node's answer is its own value plus the
    better of its children's.

    The base case is the leaf, not the missing child. A missing child has no
    path at all, which is different from a path worth zero -- so the children
    that exist are collected first and `max` is taken over those only. With
    one child there is one candidate and it wins whatever it is worth.
    """
    below = [
        best_path_sum(child) for child in (root.left, root.right) if child is not None
    ]
    return root.value + (max(below) if below else 0)
