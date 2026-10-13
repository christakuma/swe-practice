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


def min_depth(root: TreeNode | None) -> int:
    """Return the number of nodes on the shortest path from the root to a leaf.

    Breadth-first, because it visits nodes in order of depth: the first node
    with no children to come off the queue is the shallowest leaf there is,
    and nothing deeper has been looked at yet. A depth-first search has to
    finish the whole tree before it can be sure.

    The loop has no exit of its own. A non-empty tree always has a leaf, so
    the `return` inside is always reached.
    """
    if root is None:
        return 0

    queue: deque[tuple[TreeNode, int]] = deque([(root, 1)])
    while True:
        node, depth = queue.popleft()
        if node.left is None and node.right is None:
            return depth
        if node.left is not None:
            queue.append((node.left, depth + 1))
        if node.right is not None:
            queue.append((node.right, depth + 1))
