"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import TreeNode, is_mirror


def from_slots(present: tuple[int, ...]) -> TreeNode | None:
    """A tree from a level-order layout: slot i's children are 2i+1 and 2i+2.

    Each node's value is its slot number. A slot whose parent is absent is
    unreachable, so it is simply not part of the tree.
    """
    nodes = [TreeNode(slot) if here else None for slot, here in enumerate(present)]
    for slot, node in enumerate(nodes):
        if node is None:
            continue
        if 2 * slot + 1 < len(nodes):
            node.left = nodes[2 * slot + 1]
        if 2 * slot + 2 < len(nodes):
            node.right = nodes[2 * slot + 2]
    return nodes[0]


def shape(node: TreeNode | None) -> object:
    """A tree as nested tuples, so two small trees can be compared."""
    if node is None:
        return None
    return (node.value, shape(node.left), shape(node.right))


def flipped(node: TreeNode | None) -> TreeNode | None:
    """A new tree: this one reflected, built without the function under test."""
    if node is None:
        return None
    return TreeNode(node.value, flipped(node.right), flipped(node.left))


def small_trees() -> list[TreeNode | None]:
    """Every tree of up to three levels, and no tree at all."""
    return [None] + [from_slots((1, *rest)) for rest in product((0, 1), repeat=6)]


def test_accepts_a_reflection() -> None:
    """Reports True when the children have changed sides."""
    first = TreeNode(1, TreeNode(2), TreeNode(3))
    second = TreeNode(1, TreeNode(3), TreeNode(2))

    assert is_mirror(first, second) is True


def test_rejects_an_identical_copy() -> None:
    """Reports False for two identical trees that are not symmetric."""
    first = TreeNode(1, TreeNode(2), TreeNode(3))
    second = TreeNode(1, TreeNode(2), TreeNode(3))

    assert is_mirror(first, second) is False


def test_reflects_at_every_level() -> None:
    """Requires the swap at every depth, not only at the root.

    The second tree has its top two children exchanged and everything below
    them left as it was. A check that crosses over once and then compares the
    subtrees as plain copies accepts it.
    """
    first = TreeNode(1, TreeNode(2, TreeNode(4), TreeNode(5)), TreeNode(3))
    once = TreeNode(1, TreeNode(3), TreeNode(2, TreeNode(4), TreeNode(5)))
    fully = TreeNode(1, TreeNode(3), TreeNode(2, TreeNode(5), TreeNode(4)))

    assert is_mirror(first, once) is False
    assert is_mirror(first, fully) is True


def test_handles_empty_trees() -> None:
    """Treats two empty trees as mirrors, and one empty tree as not."""
    assert is_mirror(None, None) is True
    assert is_mirror(TreeNode(1), None) is False
    assert is_mirror(None, TreeNode(1)) is False


def test_compares_values_as_well_as_shape() -> None:
    """Reports False when the shapes mirror and a value differs."""
    first = TreeNode(1, TreeNode(2), TreeNode(3))
    second = TreeNode(1, TreeNode(3), TreeNode(9))

    assert is_mirror(first, second) is False


def test_accepts_every_small_tree_against_its_reflection() -> None:
    """Accepts each small tree's reflection, in both directions."""
    for tree in small_trees():
        assert is_mirror(tree, flipped(tree)) is True
        assert is_mirror(flipped(tree), tree) is True


def test_agrees_with_reflecting_and_comparing_for_every_pair() -> None:
    """Matches reflect-then-compare for every pair of small trees."""
    trees = small_trees()
    for first in trees:
        mirrored = shape(flipped(first))
        for second in trees:
            assert is_mirror(first, second) is (mirrored == shape(second))


def test_leaves_both_trees_alone() -> None:
    """Does not rearrange either tree."""
    first = TreeNode(1, TreeNode(2), TreeNode(3))
    second = TreeNode(1, TreeNode(3), TreeNode(2))

    is_mirror(first, second)

    assert shape(first) == (1, (2, None, None), (3, None, None))
    assert shape(second) == (1, (3, None, None), (2, None, None))
