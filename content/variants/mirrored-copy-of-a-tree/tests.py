"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import TreeNode, mirrored


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


def flipped_shape(node: TreeNode | None) -> object:
    """The shape a mirror image should have, computed without building one."""
    if node is None:
        return None
    return (node.value, flipped_shape(node.right), flipped_shape(node.left))


def every_node(node: TreeNode | None) -> list[TreeNode]:
    if node is None:
        return []
    return [node, *every_node(node.left), *every_node(node.right)]


def test_mirrors_a_small_tree() -> None:
    """Returns a tree with the children on opposite sides."""
    root = TreeNode(1, TreeNode(2), TreeNode(3))

    assert shape(mirrored(root)) == (1, (3, None, None), (2, None, None))


def test_mirrors_every_level() -> None:
    """Swaps children at every depth, not only at the root."""
    root = from_slots((1,) * 7)

    assert shape(mirrored(root)) == flipped_shape(root)
    assert shape(mirrored(root)) != shape(root)


def test_returns_none_for_an_empty_tree() -> None:
    """Returns None for an empty tree."""
    assert mirrored(None) is None


def test_leaves_the_original_as_it_was() -> None:
    """Does not rearrange the tree it was given."""
    root = from_slots((1, 1, 1, 1, 0, 0, 1))
    before = shape(root)

    mirrored(root)

    assert shape(root) == before


def test_shares_no_node_with_the_original() -> None:
    """Builds every node of the result afresh.

    A new root handed the original's two subtrees the other way round looks
    mirrored at the top and is the original underneath.
    """
    root = from_slots((1,) * 7)
    originals = {id(node) for node in every_node(root)}

    copy = mirrored(root)

    assert not originals & {id(node) for node in every_node(copy)}


def test_agrees_with_the_expected_shape_for_every_small_tree() -> None:
    """Matches the mirrored shape for every tree of up to four levels."""
    for rest in product((0, 1), repeat=14):
        root = from_slots((1, *rest))
        before = shape(root)
        assert shape(mirrored(root)) == flipped_shape(root), rest
        assert shape(root) == before


def test_mirroring_twice_gives_back_the_shape() -> None:
    """Returns the original shape after two mirrorings."""
    root = from_slots((1, 1, 0, 1, 1))

    assert shape(mirrored(mirrored(root))) == shape(root)
