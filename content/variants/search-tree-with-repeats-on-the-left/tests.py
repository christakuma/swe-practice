"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import TreeNode, is_search_tree


def tree(values: tuple[int | None, ...]) -> TreeNode | None:
    """A tree from a level-order layout; None is an absent node."""
    nodes = [None if value is None else TreeNode(value) for value in values]
    for slot, node in enumerate(nodes):
        if node is None:
            continue
        if 2 * slot + 1 < len(nodes):
            node.left = nodes[2 * slot + 1]
        if 2 * slot + 2 < len(nodes):
            node.right = nodes[2 * slot + 2]
    return nodes[0] if nodes else None


def values_below(node: TreeNode | None) -> list[int]:
    if node is None:
        return []
    return [node.value, *values_below(node.left), *values_below(node.right)]


def by_definition(node: TreeNode | None) -> bool:
    """Check the rule at every node against everything beneath it."""
    if node is None:
        return True
    return (
        all(value <= node.value for value in values_below(node.left))
        and all(value > node.value for value in values_below(node.right))
        and by_definition(node.left)
        and by_definition(node.right)
    )


def test_accepts_a_repeat_on_the_left() -> None:
    """Accepts an equal value as a left child."""
    assert is_search_tree(tree((2, 2, 3))) is True


def test_rejects_a_repeat_on_the_right() -> None:
    """Rejects an equal value as a right child."""
    assert is_search_tree(tree((2, 1, 2))) is False


def test_accepts_a_repeat_deep_in_the_left_subtree() -> None:
    """Accepts a repeat that is not a direct child, on the permitted side."""
    assert is_search_tree(tree((5, 3, 8, None, 5))) is True


def test_rejects_a_repeat_deep_in_the_right_subtree() -> None:
    """Rejects a repeat in the right subtree even when it is a left child."""
    assert is_search_tree(tree((5, 3, 8, None, None, 5))) is False


def test_still_rejects_values_on_the_wrong_side() -> None:
    """Rejects ordinary violations, near and far."""
    assert is_search_tree(tree((2, 3, 4))) is False
    assert is_search_tree(tree((5, 3, 8, 1, 6))) is False


def test_accepts_trivial_trees_and_negative_values() -> None:
    """Accepts an empty tree, one node, and values below zero."""
    assert is_search_tree(None) is True
    assert is_search_tree(TreeNode(7)) is True
    assert is_search_tree(tree((-5, -5, -1))) is True


def test_agrees_with_the_definition_for_every_small_tree() -> None:
    """Matches a check of the rule at every node, for every small tree.

    Every tree of up to three levels whose values are drawn from 0..2.
    """
    for values in product((None, 0, 1, 2), repeat=7):
        if values[0] is None:
            continue
        root = tree(values)
        assert is_search_tree(root) is by_definition(root), values


def test_validates_a_deep_chain_of_equal_values() -> None:
    """Accepts five hundred equal values down the left, and rejects one on the right."""
    root = TreeNode(4)
    node = root
    for _ in range(498):
        node.left = TreeNode(4)
        node = node.left

    assert is_search_tree(root) is True

    node.right = TreeNode(4)

    assert is_search_tree(root) is False
