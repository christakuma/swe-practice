"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from __future__ import annotations

from itertools import product

from solution import TreeNode, is_same_tree


def build(values: list[int | None]) -> TreeNode | None:
    """Build a tree from a level-order list, with None for a missing child."""
    if not values or values[0] is None:
        return None
    root = TreeNode(int(values[0]))
    queue = [root]
    index = 1
    while queue and index < len(values):
        node = queue.pop(0)
        for side in ("left", "right"):
            if index >= len(values):
                break
            value = values[index]
            index += 1
            if value is not None:
                child = TreeNode(int(value))
                setattr(node, side, child)
                queue.append(child)
    return root


def shape(root: TreeNode | None) -> tuple[object, ...] | None:
    """A structural fingerprint that records absent children -- an oracle."""
    if root is None:
        return None
    return (root.value, shape(root.left), shape(root.right))


def test_accepts_identical_trees() -> None:
    """Reports True for two trees with the same shape and values."""
    assert is_same_tree(build([1, 2, 3]), build([1, 2, 3])) is True


def test_rejects_different_values() -> None:
    """Reports False when a value differs."""
    assert is_same_tree(build([1, 2, 3]), build([1, 2, 4])) is False


def test_rejects_the_same_values_in_a_different_shape() -> None:
    """Reports False for the same values arranged differently.

    The discriminating test for the whole kata: one tree has a single left
    child, the other a single right child. A solution that treats a missing
    node as matching anything -- or returns True as soon as either side runs
    out -- accepts these.
    """
    assert is_same_tree(build([1, 2]), build([1, None, 2])) is False


def test_accepts_two_empty_trees() -> None:
    """Reports True for two empty trees."""
    assert is_same_tree(None, None) is True


def test_rejects_a_tree_against_an_empty_tree() -> None:
    """Reports False when only one tree is empty, either way round."""
    assert is_same_tree(build([1]), None) is False
    assert is_same_tree(None, build([1])) is False


def test_rejects_a_subtree_of_the_other() -> None:
    """Reports False when one tree is a prefix of the other.

    The second tree runs out of nodes where the first continues.
    """
    assert is_same_tree(build([1, 2, 3]), build([1, 2])) is False
    assert is_same_tree(build([1, 2]), build([1, 2, 3])) is False


def test_compares_deeply_rather_than_at_the_root() -> None:
    """Descends past matching upper levels to find a deep difference."""
    first = build([1, 2, 3, 4, 5, 6, 7])
    second = build([1, 2, 3, 4, 5, 6, 8])

    assert is_same_tree(first, second) is False


def test_handles_a_single_node() -> None:
    """Compares one-node trees by value."""
    assert is_same_tree(TreeNode(1), TreeNode(1)) is True
    assert is_same_tree(TreeNode(1), TreeNode(2)) is False


def test_handles_duplicate_values() -> None:
    """Compares by position, not by multiset of values."""
    assert is_same_tree(build([1, 1, 1]), build([1, 1, 1])) is True
    assert is_same_tree(build([1, 1]), build([1, None, 1])) is False


def test_handles_negative_values() -> None:
    """Compares negative values correctly."""
    assert is_same_tree(build([-1, -2]), build([-1, -2])) is True
    assert is_same_tree(build([-1, -2]), build([-1, 2])) is False


def test_returns_a_bool() -> None:
    """Returns True or False rather than a truthy value."""
    assert is_same_tree(TreeNode(1), TreeNode(1)) is True
    assert is_same_tree(TreeNode(1), TreeNode(2)) is False


def test_does_not_mutate_either_tree() -> None:
    """Leaves both trees as it found them."""
    first = build([1, 2, 3])
    second = build([1, 2, 3])
    before = (shape(first), shape(second))

    is_same_tree(first, second)

    assert (shape(first), shape(second)) == before


def test_agrees_with_a_structural_fingerprint_on_every_small_pair() -> None:
    """Matches a shape-recording fingerprint for every pair of small trees.

    Built from every level-order list of three slots over {1, 2, None}, so
    every combination of present and absent children in every position
    appears -- and crossed with itself, which is about seven hundred pairs.
    The shape-blindness bug needs a specific pattern of absent children to
    show up.
    """
    layouts: list[list[int | None]] = [
        list(values) for values in product([1, 2, None], repeat=3)
    ]
    trees = [build(layout) for layout in layouts]

    for first in trees:
        for second in trees:
            expected = shape(first) == shape(second)

            assert is_same_tree(first, second) is expected, (
                shape(first),
                shape(second),
            )
