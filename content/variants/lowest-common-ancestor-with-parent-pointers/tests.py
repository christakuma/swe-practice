"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc

from solution import TreeNode, lowest_common_ancestor


def child(parent: TreeNode, value: int, side: str) -> TreeNode:
    """Attach and return a new child on the given side of `parent`."""
    node = TreeNode(value, parent)
    setattr(parent, side, node)
    return node


def sample() -> dict[int, TreeNode]:
    """The tree 3 / (5 / (6, 2 / (7, 4)), 1 / (0, 8)), keyed by value."""
    nodes = {3: TreeNode(3)}
    for parent, value, side in (
        (3, 5, "left"),
        (3, 1, "right"),
        (5, 6, "left"),
        (5, 2, "right"),
        (1, 0, "left"),
        (1, 8, "right"),
        (2, 7, "left"),
        (2, 4, "right"),
    ):
        nodes[value] = child(nodes[parent], value, side)
    return nodes


def ancestors(node: TreeNode | None) -> list[TreeNode]:
    found = []
    while node is not None:
        found.append(node)
        node = node.parent
    return found


def by_listing_ancestors(first: TreeNode, second: TreeNode) -> TreeNode:
    """The first of one node's ancestors that is also among the other's."""
    above = ancestors(second)
    return next(
        node for node in ancestors(first) if any(node is other for other in above)
    )


def chain(depth: int) -> list[TreeNode]:
    nodes = [TreeNode(0)]
    for value in range(1, depth):
        nodes.append(child(nodes[-1], value, "left" if value % 2 else "right"))
    return nodes


def test_finds_the_parent_of_two_siblings() -> None:
    """Returns the shared parent of two nodes that are siblings."""
    nodes = sample()

    assert lowest_common_ancestor(nodes[6], nodes[2]) is nodes[5]
    assert lowest_common_ancestor(nodes[0], nodes[8]) is nodes[1]


def test_finds_the_root_for_nodes_on_opposite_sides() -> None:
    """Returns the root when the two nodes are in different subtrees of it."""
    nodes = sample()

    assert lowest_common_ancestor(nodes[5], nodes[1]) is nodes[3]
    assert lowest_common_ancestor(nodes[7], nodes[8]) is nodes[3]


def test_a_node_is_its_own_ancestor() -> None:
    """Returns the upper node when one of the two is above the other."""
    nodes = sample()

    assert lowest_common_ancestor(nodes[5], nodes[4]) is nodes[5]
    assert lowest_common_ancestor(nodes[4], nodes[5]) is nodes[5]
    assert lowest_common_ancestor(nodes[3], nodes[7]) is nodes[3]


def test_the_same_node_twice_is_its_own_answer() -> None:
    """Returns the node itself when both arguments are that node."""
    nodes = sample()
    alone = TreeNode(9)

    assert lowest_common_ancestor(nodes[7], nodes[7]) is nodes[7]
    assert lowest_common_ancestor(alone, alone) is alone


def test_handles_nodes_at_different_depths() -> None:
    """Finds the join when one node is several levels deeper than the other."""
    nodes = sample()

    assert lowest_common_ancestor(nodes[7], nodes[6]) is nodes[5]
    assert lowest_common_ancestor(nodes[6], nodes[4]) is nodes[5]
    assert lowest_common_ancestor(nodes[4], nodes[1]) is nodes[3]


def test_returns_the_node_and_not_its_value() -> None:
    """Returns a node object, in a tree where every node holds the same value."""
    nodes = sample()
    for node in nodes.values():
        node.value = 1

    assert lowest_common_ancestor(nodes[7], nodes[6]) is nodes[5]
    assert lowest_common_ancestor(nodes[0], nodes[4]) is nodes[3]


def test_agrees_with_listing_ancestors_for_every_pair() -> None:
    """Matches an ancestor-list search for every pair of nodes in several trees."""
    trees = [list(sample().values()), chain(9)]
    lopsided = sample()
    deep = child(child(lopsided[8], 10, "right"), 11, "left")
    trees.append([*lopsided.values(), deep, deep.parent])
    for nodes in trees:
        for first in nodes:
            for second in nodes:
                expected = by_listing_ancestors(first, second)
                assert lowest_common_ancestor(first, second) is expected


def test_leaves_the_tree_alone() -> None:
    """Changes no parent, child or value."""
    nodes = sample()
    before = [(n.value, n.parent, n.left, n.right) for n in nodes.values()]

    lowest_common_ancestor(nodes[7], nodes[0])

    assert [(n.value, n.parent, n.left, n.right) for n in nodes.values()] == before


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the depth of the tree.

    A chain of a hundred thousand nodes with one extra leaf hanging near the
    top. The answer for the bottom of the chain and that leaf is their fork,
    a hundred thousand levels above one of them. A set of ancestors holds the
    whole chain. The tree is built before measuring starts.
    """
    nodes = chain(100_000)
    twig = child(nodes[10], -1, "left" if nodes[10].left is None else "right")

    tracemalloc.start()
    found = lowest_common_ancestor(nodes[-1], twig)
    again = lowest_common_ancestor(twig, nodes[-1])
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert found is nodes[10]
    assert again is nodes[10]
    assert peak < 64_000, f"allocated {peak} bytes"
