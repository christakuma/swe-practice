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
    """Return the largest sum along any path in the tree.

    Every path has a **highest node** -- the single point where it turns from
    going up to going down. So instead of enumerating paths, consider each node
    as the turning point: the best path turning here is the best downward path
    into the left child, plus this node, plus the best downward path into the
    right child. Each node is the turn of exactly one candidate, so visiting
    every node considers every path.

    **The recursion returns one thing and records another, and that is the
    whole kata.** `descend` *returns* the best path going straight down from a
    node, because that is all its parent can use -- a parent extending into
    this subtree cannot also turn inside it. It *records* the best path turning
    here, which may use both children and is therefore useless to the parent.
    Conflating the two is the single most common way to get this wrong: return
    the turning value and the parent builds a path that visits a node twice.

    `max(descend(child), 0)` is the other half. A subtree whose best downward
    path is negative should be **skipped entirely** -- contributing nothing is
    better than contributing a loss -- and clamping at zero expresses "or take
    no child at all".

    That clamp must not reach the answer. `best` is seeded with negative
    infinity, not zero, because a path must contain at least one node: an
    all-negative tree has a negative answer and a zero floor would wrongly
    report 0. The zero is about *whether to extend into a child*; the answer is
    about *which path wins*. Two different questions that both look like "max
    with zero".

    O(n) time, every node visited once. O(h) stack.
    """
    best = float("-inf")

    def descend(node: TreeNode | None) -> int:
        """Best downward path sum from `node`, recording turns as it goes."""
        nonlocal best
        if node is None:
            return 0
        left = max(descend(node.left), 0)
        right = max(descend(node.right), 0)
        best = max(best, node.value + left + right)
        return node.value + max(left, right)

    descend(root)
    return int(best)
