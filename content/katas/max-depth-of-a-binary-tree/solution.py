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


def max_depth(root: TreeNode | None) -> int:
    """Return the number of nodes on the longest path from the root down.

    The shortest correct answer to the shortest tree question, and it is worth
    being explicit about why it is correct: the depth of a tree is one more than
    the deeper of its two subtrees, and the empty tree has depth zero. Those two
    sentences are the two lines of the function, which is what structural
    recursion looks like when the structure is doing the work.

    `root is None` is the base case rather than "a node with no children". That
    choice removes the special case: a leaf is not special, it is a node whose
    subtrees are both empty, so it gets 1 + max(0, 0) for free. Basing the
    recursion on leaves instead needs a separate branch and gets the empty tree
    wrong.

    Recursive, so it costs stack depth proportional to the depth of the tree --
    fine for balanced trees, and a RecursionError on a degenerate one past
    Python's default limit of 1000 frames. The notes have the iterative version.
    """
    if root is None:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))
