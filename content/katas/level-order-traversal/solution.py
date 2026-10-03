"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

from collections import deque


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


def level_order(root: TreeNode | None) -> list[list[int]]:
    """Return the values level by level, top to bottom, left to right.

    A plain breadth-first traversal visits nodes in exactly this order and
    cannot tell you where one level ends -- which is the only difficulty here.
    Two ways to recover the boundary, and the one below is the one worth knowing:
    **read the queue's length before draining it**, because at that instant the
    queue holds precisely one level.

    The alternative is to push `(node, depth)` pairs and group afterwards, which
    works, carries a depth per node, and makes the result a grouping problem
    rather than a traversal.

    `deque` rather than a list, because `list.pop(0)` is O(n) -- it shifts every
    remaining element -- and that turns a linear traversal into a quadratic one
    on a wide tree. It is the most common accidental quadratic in Python, and
    the fix is an import.
    """
    if root is None:
        return []

    levels: list[list[int]] = []
    queue: deque[TreeNode] = deque([root])
    while queue:
        width = len(queue)
        level = []
        for _ in range(width):
            node = queue.popleft()
            level.append(node.value)
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        levels.append(level)
    return levels
