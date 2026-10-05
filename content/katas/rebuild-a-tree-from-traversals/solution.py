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


def rebuild(preorder: list[int], inorder: list[int]) -> TreeNode | None:
    """Rebuild the tree from its pre-order and in-order traversals.

    Each traversal supplies exactly one fact the other cannot:

    - **pre-order names the root** -- it is visited first, so `preorder[0]`;
    - **in-order locates the split** -- the entire left subtree is visited
      before the root, so the root's position in `inorder` says how big the
      left subtree is.

    Neither alone is enough, and that is why the problem specifies two. One
    traversal is consistent with many trees; pre-order plus in-order pins it
    exactly, *given distinct values*. With duplicates the root's position in
    `inorder` is ambiguous and the tree is no longer recoverable, which is why
    the prompt rules them out rather than as a convenience.

    Two things make this O(n) rather than O(n^2), and they are easy to lose:

    `position` is built once. Searching `inorder` for the root on every call is
    O(n) per node and is the usual reason this comes out quadratic.

    The recursion passes **index ranges, not slices**. Slicing the lists is the
    natural way to express "the left part" and copies O(n) elements per call,
    which reintroduces exactly the cost the dictionary removed. `pre_start` and
    the in-order bounds carry the same information for free.

    `left_size` is the only arithmetic here, and it is the whole trick: it is
    computed from the in-order split and then used to cut the *pre-order*
    range, because the two traversals agree about subtree sizes even though
    they disagree about order.
    """
    position = {value: index for index, value in enumerate(inorder)}

    def construct(pre_start: int, in_start: int, in_stop: int) -> TreeNode | None:
        if in_start > in_stop:
            return None
        value = preorder[pre_start]
        split = position[value]
        left_size = split - in_start
        return TreeNode(
            value,
            construct(pre_start + 1, in_start, split - 1),
            construct(pre_start + 1 + left_size, split + 1, in_stop),
        )

    return construct(0, 0, len(inorder) - 1)
