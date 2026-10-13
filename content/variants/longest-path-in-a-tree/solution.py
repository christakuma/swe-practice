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


def longest_path(root: TreeNode | None) -> int:
    """Return the number of nodes on the longest path in the tree.

    Each node reports upwards the length of the longest path running straight
    down from it. On the way, it considers the one path it alone can make:
    down its left side, through itself, and down its right. The answer is the
    longest of those across the whole tree.

    The two are different numbers and must not be confused. A parent can only
    extend a path that does not turn, so what is returned is `1 + max(...)`;
    what is recorded is `1 + left + right`.
    """
    best = 0

    def down(node: TreeNode | None) -> int:
        nonlocal best
        if node is None:
            return 0
        left = down(node.left)
        right = down(node.right)
        best = max(best, left + right + 1)
        return 1 + max(left, right)

    down(root)
    return best
