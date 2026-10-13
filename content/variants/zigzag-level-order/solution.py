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
    """Return the values level by level, alternating direction.

    The traversal is the ordinary one and does not change: nodes enter the
    queue left to right at every level. What alternates is only how a
    finished level is *reported*, so the flip is applied to the list after it
    is complete and never to the order children are enqueued in -- reversing
    that would scramble every level below.
    """
    if root is None:
        return []

    levels: list[list[int]] = []
    queue: deque[TreeNode] = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.value)
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        levels.append(level[::-1] if len(levels) % 2 else level)
    return levels
