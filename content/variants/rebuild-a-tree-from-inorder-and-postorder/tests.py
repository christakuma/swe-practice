"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import TreeNode, rebuild


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


def in_order(node: TreeNode | None) -> list[int]:
    if node is None:
        return []
    return [*in_order(node.left), node.value, *in_order(node.right)]


def post_order(node: TreeNode | None) -> list[int]:
    if node is None:
        return []
    return [*post_order(node.left), *post_order(node.right), node.value]


def test_rebuilds_the_documented_tree() -> None:
    """Rebuilds the worked example."""
    tree = rebuild([9, 3, 15, 20, 7], [9, 15, 7, 20, 3])

    assert shape(tree) == (3, (9, None, None), (20, (15, None, None), (7, None, None)))


def test_puts_a_lone_child_on_the_correct_side() -> None:
    """Tells a left child from a right one with the same post-order."""
    assert shape(rebuild([2, 1], [2, 1])) == (1, (2, None, None), None)
    assert shape(rebuild([1, 2], [2, 1])) == (1, None, (2, None, None))


def test_handles_empty_and_single_node_trees() -> None:
    """Returns None for empty lists and one node for one value."""
    assert rebuild([], []) is None
    assert shape(rebuild([5], [5])) == (5, None, None)


def test_rebuilds_chains() -> None:
    """Rebuilds trees that lean entirely one way."""
    assert shape(rebuild([1, 2, 3], [1, 2, 3])) == (3, (2, (1, None, None), None), None)
    assert shape(rebuild([1, 2, 3], [3, 2, 1])) == (1, None, (2, None, (3, None, None)))


def test_rebuilds_every_small_tree_from_its_own_traversals() -> None:
    """Rebuilds every tree of up to four levels from its own traversals."""
    for rest in product((0, 1), repeat=14):
        original = from_slots((1, *rest))
        rebuilt = rebuild(in_order(original), post_order(original))
        assert shape(rebuilt) == shape(original), rest


def test_returns_tree_nodes_and_leaves_the_lists_alone() -> None:
    """Returns TreeNode objects and does not modify either list."""
    inorder, postorder = [9, 3, 15], [9, 15, 3]

    tree = rebuild(inorder, postorder)

    assert isinstance(tree, TreeNode)
    assert (inorder, postorder) == ([9, 3, 15], [9, 15, 3])


def test_rebuilds_a_large_tree() -> None:
    """Rebuilds a balanced tree of sixty thousand nodes within the time limit."""
    size = 65_535
    original = from_slots((1,) * size)

    rebuilt = rebuild(in_order(original), post_order(original))

    assert rebuilt is not None
    assert rebuilt.value == 0
    assert in_order(rebuilt) == in_order(original)
    assert post_order(rebuilt) == post_order(original)
