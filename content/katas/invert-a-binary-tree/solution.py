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


def invert(root: TreeNode | None) -> TreeNode | None:
    """Mirror the tree in place and return the root.

    Swap the root's children, then solve the same problem on each of them.
    There is no accumulator, no traversal order to choose and nothing to
    combine -- which makes this the cleanest example in the library of a
    problem whose recursive structure *is* its solution.

    Returning early on None does two jobs: it handles the empty tree and it
    terminates the recursion at the leaves, so no separate leaf check is
    needed.

    **Swapping before or after the recursive calls is genuinely equivalent
    here**, which is unusual and worth understanding rather than noticing. The
    two calls operate on disjoint subtrees, so neither can observe the other's
    work, and the swap only rewrites pointers *at this node*. Nothing in the
    recursion reads a pointer the swap changes. Most tree algorithms do not
    have that freedom -- anything that accumulates a result, or whose recursion
    depends on where it is in the tree, cares a great deal about pre- versus
    post-order.

    `O(n)` time, every node visited once. `O(h)` space for the call stack --
    which is `O(log n)` for a balanced tree and `O(n)` for a degenerate one, so
    a tree that is a linked list will exhaust the recursion limit. An explicit
    stack or queue fixes that and is the right choice when the depth is not
    known to be bounded.
    """
    if root is None:
        return None
    root.left, root.right = invert(root.right), invert(root.left)
    return root
