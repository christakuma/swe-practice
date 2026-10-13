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


def swapped_values(root: TreeNode | None) -> tuple[int, int] | None:
    """Return the two values whose exchange broke a search tree.

    Read in order, a valid search tree is an ascending sequence, and
    exchanging two of its values leaves it ascending except at one or two
    **drops** -- places where a value is followed by a smaller one.

    If the two values were neighbours in the sequence there is one drop, and
    it is the pair itself. If they were further apart there are two: the
    larger value now sits early and is followed by something smaller, and
    the smaller value sits late and is preceded by something larger.

    Both cases are covered by one rule. The larger value is the first value
    of the first drop; the smaller is the second value of the last drop. The
    walk records both at the first drop and overwrites the second at a later
    one.

    The traversal uses an explicit stack, since the tree may be a chain.
    """
    larger = smaller = previous = None
    stack: list[TreeNode] = []
    node = root
    while stack or node is not None:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()
        if previous is not None and node.value < previous:
            if larger is None:
                larger = previous
            smaller = node.value
        previous = node.value
        node = node.right
    return None if larger is None or smaller is None else (smaller, larger)
