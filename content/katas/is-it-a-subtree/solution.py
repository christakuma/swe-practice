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


def _same(first: TreeNode | None, second: TreeNode | None) -> bool:
    """Whether two trees have identical shape and values.

    Exactly `are-two-trees-the-same`, and the middle base case is load-bearing
    for the same reason: a missing node must not match a present one, or
    "complete subtree" silently becomes "subtree with at least these nodes".
    """
    if first is None and second is None:
        return True
    if first is None or second is None:
        return False
    return (
        first.value == second.value
        and _same(first.left, second.left)
        and _same(first.right, second.right)
    )


def is_subtree(tree: TreeNode | None, candidate: TreeNode | None) -> bool:
    """Return whether `candidate` appears in `tree` as a complete subtree.

    **Two different questions, so two functions.** "Are these identical?" is
    not "does this contain that?", and trying to answer both in one recursion
    is where this problem goes wrong -- the recursion has to be able to *fail*
    a match at one node and keep searching elsewhere, which a single function
    comparing both trees in step cannot express.

    So: at each node, either the subtree rooted here is the candidate, or the
    answer lies in the left subtree, or in the right one. The identity check is
    `_same`, lifted wholesale from `are-two-trees-the-same`.

    An empty candidate is a subtree of anything -- including the empty tree --
    which is the `candidate is None` branch and also means the search succeeds
    immediately rather than walking. A non-empty candidate cannot be found in
    an empty tree, which is the next branch.

    O(n * m) in the worst case: every node of `tree` may start a comparison
    that walks most of `candidate`. The usual improvement is to serialise both
    trees -- recording absent children, which is what makes the serialisation
    faithful -- and ask whether one string contains the other, which is O(n + m)
    with a proper substring search. That is a genuinely better algorithm and it
    needs the serialisation to be unambiguous, so it is really the same lesson
    as `encode-and-decode-strings` wearing a different hat.
    """
    if candidate is None:
        return True
    if tree is None:
        return False
    return (
        _same(tree, candidate)
        or is_subtree(tree.left, candidate)
        or is_subtree(tree.right, candidate)
    )
