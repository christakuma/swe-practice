"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class TreeNode:
    """A binary tree node. Values are distinct within a tree."""

    def __init__(
        self,
        value: int,
        left: TreeNode | None = None,
        right: TreeNode | None = None,
    ) -> None:
        self.value = value
        self.left = left
        self.right = right


def lowest_common_ancestor(
    root: TreeNode | None, first: int, second: int
) -> int | None:
    """Return the value of the deepest node that has both values below it.

    The recursion is three lines and the whole insight is what it returns: "the
    ancestor if I found it, or whichever of the two values I found, or nothing".
    Overloading one return value like that is unusual enough to be worth saying
    out loud -- it is what lets a parent conclude, from two non-None answers,
    that the split happens here and it is the ancestor.

    This tree is not a search tree, so there is no ordering to steer by and every
    node may have to be visited. On a search tree the same problem is O(h): both
    values on the same side means recurse that way, otherwise this node is the
    answer, and no backtracking is needed.

    The missing-value case is why this returns `None` rather than a node, and why
    it is checked separately before recursing. Without the presence check, asking
    for a value that is not in the tree returns the other value's own position --
    a confident wrong answer rather than a refusal.
    """
    if not _contains(root, first) or not _contains(root, second):
        return None
    return _search(root, first, second)


def _contains(node: TreeNode | None, value: int) -> bool:
    """Whether `value` appears anywhere in this subtree."""
    if node is None:
        return False
    if node.value == value:
        return True
    return _contains(node.left, value) or _contains(node.right, value)


def _search(node: TreeNode | None, first: int, second: int) -> int | None:
    """The ancestor, or whichever of the two values this subtree holds."""
    if node is None:
        return None
    if node.value in (first, second):
        return node.value
    left = _search(node.left, first, second)
    right = _search(node.right, first, second)
    if left is not None and right is not None:
        return node.value
    return left if left is not None else right
