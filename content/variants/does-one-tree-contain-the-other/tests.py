"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import TreeNode, is_subtree


def tree_of(values: tuple[int | None, ...]) -> TreeNode | None:
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


def as_tuple(node: TreeNode | None) -> tuple | None:
    if node is None:
        return None
    return (node.value, as_tuple(node.left), as_tuple(node.right))


def overlays(whole: tuple | None, part: tuple | None) -> bool:
    if part is None:
        return True
    if whole is None or whole[0] != part[0]:
        return False
    return overlays(whole[1], part[1]) and overlays(whole[2], part[2])


def by_tuples(whole: tuple | None, part: tuple | None) -> bool:
    """Try the overlay at the root, then in each child, on plain tuples."""
    if part is None:
        return True
    if whole is None:
        return False
    return (
        overlays(whole, part) or by_tuples(whole[1], part) or by_tuples(whole[2], part)
    )


def test_allows_the_tree_to_continue_below_the_candidate() -> None:
    """Accepts a match where the tree has nodes the candidate lacks."""
    tree = tree_of((3, 4, 5, 1, 2, None, None, None, None, 0))
    candidate = tree_of((4, 1, 2))

    assert is_subtree(tree, candidate) is True


def test_does_not_allow_the_candidate_to_continue_below_the_tree() -> None:
    """Rejects a candidate with a node where the tree has none."""
    assert is_subtree(tree_of((3, 4, 5, 1)), tree_of((4, 1, 2))) is False


def test_matches_at_the_root_and_at_a_leaf() -> None:
    """Finds a candidate at the top of the tree and at the bottom."""
    tree = tree_of((1, 2, 3))

    assert is_subtree(tree, tree_of((1, 2))) is True
    assert is_subtree(tree, tree_of((3,))) is True


def test_positions_matter() -> None:
    """Rejects a candidate whose child is on the other side."""
    assert is_subtree(tree_of((1, 2)), tree_of((1, None, 2))) is False


def test_handles_empty_trees() -> None:
    """Finds the empty candidate anywhere, and nothing in an empty tree."""
    assert is_subtree(None, None) is True
    assert is_subtree(TreeNode(1), None) is True
    assert is_subtree(None, TreeNode(1)) is False


def test_finds_a_later_match_after_a_partial_one() -> None:
    """Keeps looking after a node that matches only part of the candidate."""
    tree = tree_of((1, 1, None, 1, None, None, None, 2))
    candidate = tree_of((1, 2))

    assert is_subtree(tree, candidate) is True


def test_agrees_with_an_overlay_on_tuples_for_every_small_pair() -> None:
    """Matches a tuple-based check for every small tree and candidate."""
    candidates = [None] + [
        tree_of(values)
        for values in product((None, 0, 1), repeat=3)
        if values[0] is not None
    ]
    for values in product((None, 0, 1), repeat=7):
        if values[0] is None:
            continue
        tree = tree_of(values)
        for candidate in candidates:
            expected = by_tuples(as_tuple(tree), as_tuple(candidate))
            assert is_subtree(tree, candidate) is expected, (
                values,
                as_tuple(candidate),
            )


def test_leaves_both_trees_alone() -> None:
    """Does not rearrange either tree."""
    tree, candidate = tree_of((1, 2, 3)), tree_of((1, 2))

    is_subtree(tree, candidate)

    assert as_tuple(tree) == (1, (2, None, None), (3, None, None))
    assert as_tuple(candidate) == (1, (2, None, None), None)
