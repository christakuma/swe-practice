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


def is_subtree(tree: TreeNode | None, candidate: TreeNode | None) -> bool:
    """Return whether `candidate` fits over part of `tree`, from some node down.

    Two recursions, as in the exact version. `covers` lays the candidate
    over one position, and its base cases are the whole difference: the
    candidate running out is a success, whatever the tree still holds there;
    the tree running out first is a failure. The outer loop then tries every
    node of the tree as the place to lay it.
    """

    def covers(node: TreeNode | None, pattern: TreeNode | None) -> bool:
        if pattern is None:
            return True
        if node is None or node.value != pattern.value:
            return False
        return covers(node.left, pattern.left) and covers(node.right, pattern.right)

    def anywhere(node: TreeNode | None) -> bool:
        if node is None:
            return False
        return covers(node, candidate) or anywhere(node.left) or anywhere(node.right)

    return candidate is None or anywhere(tree)
