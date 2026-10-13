"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import TreeNode, longest_path


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


def reachable(present: tuple[int, ...]) -> list[int]:
    """The slots that are actually part of the tree."""
    found = []
    for slot, here in enumerate(present):
        if here and (slot == 0 or (slot - 1) // 2 in found):
            found.append(slot)
    return found


def nodes_between(first: int, second: int) -> int:
    """How many nodes lie on the path between two slots, by climbing to meet."""
    count = 1
    while first != second:
        if first > second:
            first = (first - 1) // 2
        else:
            second = (second - 1) // 2
        count += 1
    return count


def test_finds_a_path_through_the_root() -> None:
    """Counts the nodes on a path that passes through the root."""
    root = TreeNode(1, TreeNode(2, TreeNode(4), TreeNode(5)), TreeNode(3))

    assert longest_path(root) == 4


def test_finds_a_path_that_avoids_the_root() -> None:
    """Finds the longest path when it turns below the root."""
    root = TreeNode(
        1, TreeNode(2, TreeNode(3, TreeNode(4)), TreeNode(5, None, TreeNode(6)))
    )

    assert longest_path(root) == 5


def test_handles_an_empty_tree_and_a_single_node() -> None:
    """Returns 0 for an empty tree and 1 for one node."""
    assert longest_path(None) == 0
    assert longest_path(TreeNode(7)) == 1


def test_counts_nodes_not_edges() -> None:
    """Counts two nodes for a parent and child, not one edge."""
    assert longest_path(TreeNode(1, TreeNode(2))) == 2
    assert longest_path(TreeNode(1, TreeNode(2), TreeNode(3))) == 3


def test_ignores_the_values() -> None:
    """Measures shape only, whatever the nodes hold."""
    root = TreeNode(-1000, TreeNode(-1000, TreeNode(-1000)), TreeNode(1000))

    assert longest_path(root) == 4


def test_measures_a_chain() -> None:
    """Returns the full length of a chain five hundred deep."""
    root = TreeNode(0)
    node = root
    for value in range(1, 500):
        node.left = TreeNode(value)
        node = node.left

    assert longest_path(root) == 500


def test_agrees_with_measuring_every_pair_of_nodes() -> None:
    """Matches the longest of every node-to-node path, for thousands of trees."""
    for mask in range(0, 2**14, 3):
        present = (1, *((mask >> bit) & 1 for bit in range(14)))
        slots = reachable(present)
        expected = max(nodes_between(a, b) for a in slots for b in slots)
        assert longest_path(from_slots(present)) == expected, present


def test_returns_an_int() -> None:
    """Returns an int rather than a float or a bool."""
    assert type(longest_path(TreeNode(1))) is int
