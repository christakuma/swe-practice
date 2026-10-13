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


def best_haul(root: TreeNode | None) -> int:
    """Return the largest total of nodes no two of which share an edge.

    The row version carried two numbers along the row: the best total with
    the last house taken and the best with it left. The same two numbers come
    up from each subtree here -- best with its root taken, best with its root
    left.

    - Taking a node forbids its children, so it adds each child's *left*
      number to its own value.
    - Leaving a node puts no condition on its children, so it adds whichever
      of each child's two numbers is larger. Not "the child's taken number":
      leaving two nodes in a row is allowed and is sometimes right.
    """

    def haul(node: TreeNode | None) -> tuple[int, int]:
        """(best with `node` taken, best with `node` left)."""
        if node is None:
            return 0, 0
        left_taken, left_left = haul(node.left)
        right_taken, right_left = haul(node.right)
        taken = node.value + left_left + right_left
        left = max(left_taken, left_left) + max(right_taken, right_left)
        return taken, left

    return max(haul(root))
