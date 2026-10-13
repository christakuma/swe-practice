"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import TreeNode, min_depth


def from_slots(present: tuple[int, ...]) -> TreeNode | None:
    """A tree from a level-order layout: slot i's children are 2i+1 and 2i+2."""
    nodes = [TreeNode(slot) if here else None for slot, here in enumerate(present)]
    for slot, node in enumerate(nodes):
        if node is None:
            continue
        if 2 * slot + 1 < len(nodes):
            node.left = nodes[2 * slot + 1]
        if 2 * slot + 2 < len(nodes):
            node.right = nodes[2 * slot + 2]
    return nodes[0]


def leaf_depths(node: TreeNode | None, depth: int = 1) -> list[int]:
    """The depth of every leaf, found by walking every path to its end."""
    if node is None:
        return []
    if node.left is None and node.right is None:
        return [depth]
    return leaf_depths(node.left, depth + 1) + leaf_depths(node.right, depth + 1)


def chain(length: int) -> TreeNode:
    """`length` nodes, each the left child of the one before."""
    root = TreeNode(0)
    node = root
    for value in range(1, length):
        node.left = TreeNode(value)
        node = node.left
    return root


def test_finds_the_shallowest_leaf() -> None:
    """Returns the depth of the nearest leaf, not the furthest."""
    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))

    assert min_depth(root) == 2


def test_does_not_stop_at_a_missing_child() -> None:
    """Does not treat a node with one child as a leaf."""
    assert min_depth(TreeNode(1, TreeNode(2))) == 2
    assert min_depth(TreeNode(1, None, TreeNode(2))) == 2


def test_follows_a_chain_to_its_only_leaf() -> None:
    """Returns the full length of a chain, which has one leaf at the bottom."""
    assert min_depth(chain(4)) == 4


def test_handles_an_empty_tree_and_a_single_node() -> None:
    """Returns 0 for an empty tree and 1 for one node."""
    assert min_depth(None) == 0
    assert min_depth(TreeNode(7)) == 1


def test_takes_the_shallower_side() -> None:
    """Returns the shallower side whichever side it is on."""
    deep_left = TreeNode(1, chain(5), TreeNode(2))
    deep_right = TreeNode(1, TreeNode(2), chain(5))

    assert min_depth(deep_left) == 2
    assert min_depth(deep_right) == 2


def test_looks_past_a_one_child_node_part_way_down() -> None:
    """Keeps going past a node with one child anywhere in the tree."""
    root = TreeNode(1, TreeNode(2, TreeNode(4)), TreeNode(3, None, TreeNode(5)))

    assert min_depth(root) == 3


def test_agrees_with_walking_every_path_for_every_small_tree() -> None:
    """Matches the shallowest of every root-to-leaf path, for every small tree."""
    for rest in product((0, 1), repeat=14):
        root = from_slots((1, *rest))
        assert min_depth(root) == min(leaf_depths(root)), rest


def test_returns_an_int() -> None:
    """Returns an int rather than a float or a bool."""
    assert type(min_depth(TreeNode(1))) is int


def test_does_not_descend_a_deep_side_to_find_a_shallow_leaf() -> None:
    """Finds a leaf at depth two beside a chain a hundred thousand deep.

    A recursive search goes down the chain first and runs out of stack long
    before it gets back to look at the other child. Breadth-first reaches the
    leaf on its third node.
    """
    root = TreeNode(1, chain(100_000), TreeNode(2))

    assert min_depth(root) == 2


def test_measures_a_tree_that_is_only_a_deep_chain() -> None:
    """Measures a chain a hundred thousand nodes long without recursing."""
    assert min_depth(chain(100_000)) == 100_000
