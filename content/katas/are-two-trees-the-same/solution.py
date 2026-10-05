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


def is_same_tree(first: TreeNode | None, second: TreeNode | None) -> bool:
    """Return whether two trees have the same shape and values.

    The definition is the program: two trees are the same when their roots
    match and both pairs of subtrees are the same.

    **There are three base cases and the middle one is the whole exercise.**

    - both None: the same, trivially;
    - exactly one None: *not* the same -- this is what makes shape matter;
    - values differ: not the same.

    Collapse the second case -- by treating a missing node as matching
    anything, or by returning True whenever either side is None -- and the
    function stops comparing structure. A chain of 1-2 going left then becomes
    equal to a chain of 1-2 going right, because the comparison never reaches
    a node to disagree about.

    `first is second` as the first check would also pass both-None, and would
    additionally short-circuit on two references to the same tree. That is a
    real optimisation and a misleading one in a teaching solution, because it
    makes the structural case look like an identity case.

    The `and`s short-circuit, so a mismatch near the root stops immediately:
    O(n) in the worst case but often far less, which is why the bound is
    stated against the smaller tree.
    """
    if first is None and second is None:
        return True
    if first is None or second is None:
        return False
    return (
        first.value == second.value
        and is_same_tree(first.left, second.left)
        and is_same_tree(first.right, second.right)
    )
