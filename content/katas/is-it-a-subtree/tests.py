"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from __future__ import annotations

from itertools import product

from solution import TreeNode, is_subtree


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
    """A structural fingerprint that records absent children."""
    if root is None:
        return None
    return (root.value, shape(root.left), shape(root.right))


def every_shape(root: TreeNode | None) -> list[tuple[object, ...] | None]:
    """The fingerprint of every subtree of `root` -- an independent oracle."""
    if root is None:
        return [None]
    return [shape(root), *every_shape(root.left), *every_shape(root.right)]


def test_finds_a_subtree() -> None:
    """Reports True when the candidate sits inside the tree."""
    tree = build([3, 4, 5, 1, 2])
    candidate = build([4, 1, 2])

    assert is_subtree(tree, candidate) is True


def test_rejects_a_near_match_with_an_extra_child() -> None:
    """Reports False when a matching node has a descendant the candidate lacks.

    The discriminating test for the whole kata. Node 4 has the right value and
    the right children, but one of them carries an extra child -- so the
    subtree rooted at 4 is not the candidate. A comparison that stops when the
    candidate runs out accepts this.
    """
    tree = build([3, 4, 5, 1, 2, None, None, None, None, 0])
    candidate = build([4, 1, 2])

    assert is_subtree(tree, candidate) is False


def test_finds_the_whole_tree_as_its_own_subtree() -> None:
    """Reports True when the candidate is the entire tree."""
    tree = build([1, 2, 3])

    assert is_subtree(tree, build([1, 2, 3])) is True


def test_finds_a_leaf() -> None:
    """Reports True for a single-node candidate that appears as a leaf."""
    tree = build([1, 2, 3])

    assert is_subtree(tree, TreeNode(2)) is True
    assert is_subtree(tree, TreeNode(3)) is True


def test_rejects_a_single_node_that_is_not_a_leaf_in_the_tree() -> None:
    """Reports False for a bare node whose counterpart has children.

    The tree holds a 2, but that 2 has a child -- so the subtree rooted there
    is not a single node.
    """
    tree = build([1, 2, 3, 4])

    assert is_subtree(tree, TreeNode(2)) is False


def test_handles_an_empty_candidate() -> None:
    """Reports True for an empty candidate, in any tree including none."""
    assert is_subtree(build([1, 2]), None) is True
    assert is_subtree(None, None) is True


def test_handles_an_empty_tree() -> None:
    """Reports False when a non-empty candidate is sought in an empty tree."""
    assert is_subtree(None, TreeNode(1)) is False


def test_rejects_an_absent_candidate() -> None:
    """Reports False when the candidate's values are not in the tree."""
    assert is_subtree(build([1, 2, 3]), TreeNode(9)) is False


def test_searches_the_right_subtree_too() -> None:
    """Finds a candidate that is only reachable down the right branch."""
    tree = build([1, 2, 3, None, None, 4, 5])
    candidate = build([3, 4, 5])

    assert is_subtree(tree, candidate) is True


def test_keeps_searching_after_a_failed_match() -> None:
    """Finds a later match after an earlier node matched only partially.

    The first 2 encountered has a child and cannot match; the second 2 is a
    leaf and can. A solution that commits to the first value match and then
    fails reports False.
    """
    tree = build([1, 2, 2, 4])
    candidate = TreeNode(2)

    assert is_subtree(tree, candidate) is True


def test_handles_duplicate_values() -> None:
    """Distinguishes identically valued nodes by their subtrees."""
    tree = build([1, 1, 1])

    assert is_subtree(tree, build([1, 1, 1])) is True
    assert is_subtree(tree, build([1, 1])) is False


def test_returns_a_bool() -> None:
    """Returns True or False rather than a truthy value."""
    assert is_subtree(build([1, 2]), TreeNode(2)) is True
    assert is_subtree(build([1, 2]), TreeNode(3)) is False


def test_agrees_with_an_oracle_on_every_small_pair() -> None:
    """Matches "is the candidate's fingerprint among the tree's subtrees".

    Every level-order layout of four slots over {1, 2, None} as the tree,
    crossed with every layout of three as the candidate -- around two thousand
    pairs. The extra-child bug needs a candidate that is a proper prefix of
    some subtree, which only some layouts provide.
    """
    trees = [build(list(values)) for values in product([1, 2, None], repeat=4)]
    candidates = [build(list(values)) for values in product([1, 2, None], repeat=3)]

    for tree in trees:
        available = every_shape(tree)
        for candidate in candidates:
            expected = shape(candidate) in available

            assert is_subtree(tree, candidate) is expected, (
                shape(tree),
                shape(candidate),
            )
