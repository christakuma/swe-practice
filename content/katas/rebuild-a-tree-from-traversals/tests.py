"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from solution import TreeNode, rebuild

if TYPE_CHECKING:
    from collections.abc import Iterator


def shapes(count: int) -> list[object]:
    """Every binary tree shape with `count` nodes, as nested tuples."""
    if count == 0:
        return [None]
    out: list[object] = []
    for left_size in range(count):
        for left in shapes(left_size):
            for right in shapes(count - 1 - left_size):
                out.append((left, right))
    return out


def fill(shape: object, source: Iterator[int]) -> TreeNode | None:
    """Fill a shape with values from `source`, in pre-order."""
    if not isinstance(shape, tuple):
        return None
    node = TreeNode(next(source))
    node.left = fill(shape[0], source)
    node.right = fill(shape[1], source)
    return node


def preorder_of(root: TreeNode | None) -> list[int]:
    """Root, then left subtree, then right subtree."""
    if root is None:
        return []
    return [root.value, *preorder_of(root.left), *preorder_of(root.right)]


def inorder_of(root: TreeNode | None) -> list[int]:
    """Left subtree, then root, then right subtree."""
    if root is None:
        return []
    return [*inorder_of(root.left), root.value, *inorder_of(root.right)]


def fingerprint(root: TreeNode | None) -> object:
    """A structural fingerprint that records absent children."""
    if root is None:
        return None
    return (root.value, fingerprint(root.left), fingerprint(root.right))


def test_rebuilds_the_worked_example() -> None:
    """Rebuilds the documented tree."""
    tree = rebuild([3, 9, 20, 15, 7], [9, 3, 15, 20, 7])

    assert fingerprint(tree) == (
        3,
        (9, None, None),
        (20, (15, None, None), (7, None, None)),
    )


def test_handles_empty_input() -> None:
    """Returns None for empty traversals."""
    assert rebuild([], []) is None


def test_handles_a_single_node() -> None:
    """Rebuilds a one-node tree."""
    assert fingerprint(rebuild([1], [1])) == (1, None, None)


def test_rebuilds_a_left_only_chain() -> None:
    """Rebuilds a tree with no right children.

    In-order is the reverse of pre-order here, so the root sits at the end of
    the in-order list and the left subtree takes everything.
    """
    tree = rebuild([3, 2, 1], [1, 2, 3])

    assert fingerprint(tree) == (3, (2, (1, None, None), None), None)


def test_rebuilds_a_right_only_chain() -> None:
    """Rebuilds a tree with no left children.

    The mirror case: the root is first in both lists and the left subtree is
    empty every time, which is where an unguarded range check recurses forever.
    """
    tree = rebuild([1, 2, 3], [1, 2, 3])

    assert fingerprint(tree) == (1, None, (2, None, (3, None, None)))


def test_distinguishes_a_left_child_from_a_right_child() -> None:
    """Puts a lone child on the correct side.

    Both trees have pre-order [1, 2]; only the in-order list says which side
    the 2 is on. A solution that ignores in-order entirely still passes the
    full-tree cases.
    """
    assert fingerprint(rebuild([1, 2], [2, 1])) == (1, (2, None, None), None)
    assert fingerprint(rebuild([1, 2], [1, 2])) == (1, None, (2, None, None))


def test_handles_negative_values() -> None:
    """Rebuilds a tree whose values are negative."""
    tree = rebuild([-1, -2, -3], [-2, -1, -3])

    assert fingerprint(tree) == (-1, (-2, None, None), (-3, None, None))


def test_round_trips_every_shape_up_to_eight_nodes() -> None:
    """Rebuilds every binary tree shape from its own traversals.

    Two thousand shapes -- every arrangement of up to eight nodes. This is the
    test that matters: the left-size arithmetic that cuts the pre-order range
    is the only hard part, and an off-by-one in it survives the hand-picked
    cases above at some shapes and not others.
    """
    for count in range(9):
        for shape in shapes(count):
            original = fill(shape, iter(range(count)))

            rebuilt = rebuild(preorder_of(original), inorder_of(original))

            assert fingerprint(rebuilt) == fingerprint(original), (count, shape)


def test_returns_real_tree_nodes() -> None:
    """Returns TreeNode objects rather than tuples or dicts."""
    tree = rebuild([1, 2], [2, 1])

    assert isinstance(tree, TreeNode)
    assert isinstance(tree.left, TreeNode)
    assert tree.right is None


def test_does_not_mutate_its_inputs() -> None:
    """Leaves both traversal lists as it found them.

    Popping from the front of the pre-order list is a common way to track
    position and destroys the caller's data.
    """
    preorder = [3, 9, 20, 15, 7]
    inorder = [9, 3, 15, 20, 7]
    before = (list(preorder), list(inorder))

    rebuild(preorder, inorder)

    assert (preorder, inorder) == before


def test_rebuilds_a_large_balanced_tree() -> None:
    """Rebuilds a tree of sixty thousand nodes within the time limit.

    Searching the in-order list per node is O(n^2) -- a few billion
    comparisons here -- and slicing the lists per call is the same cost again
    in copying.
    """
    values = list(range(65_535))

    def balanced(low: int, high: int) -> TreeNode | None:
        if low > high:
            return None
        middle = (low + high) // 2
        return TreeNode(
            values[middle], balanced(low, middle - 1), balanced(middle + 1, high)
        )

    original = balanced(0, len(values) - 1)
    preorder = preorder_of(original)
    inorder = inorder_of(original)

    rebuilt = rebuild(preorder, inorder)

    assert inorder_of(rebuilt) == inorder
    assert preorder_of(rebuilt) == preorder
