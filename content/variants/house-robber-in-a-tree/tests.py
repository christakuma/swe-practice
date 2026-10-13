"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator
from itertools import product

from solution import TreeNode, best_haul

type Shape = tuple["Shape", "Shape"] | None


def shapes(size: int) -> Iterator[Shape]:
    """Every binary tree shape with `size` nodes."""
    if size == 0:
        yield None
        return
    for on_left in range(size):
        for left in shapes(on_left):
            for right in shapes(size - 1 - on_left):
                yield (left, right)


def grow(shape: Shape, values: Iterator[int]) -> TreeNode | None:
    """A tree of the given shape, filled with values in pre-order."""
    if shape is None:
        return None
    value = next(values)
    return TreeNode(value, grow(shape[0], values), grow(shape[1], values))


def by_trying_every_set(root: TreeNode | None) -> int:
    """The best total over every set of nodes with no parent and child together."""
    nodes: list[TreeNode] = []
    edges: list[tuple[int, int]] = []
    stack = [(root, -1)]
    while stack:
        node, parent = stack.pop()
        if node is None:
            continue
        index = len(nodes)
        nodes.append(node)
        if parent >= 0:
            edges.append((parent, index))
        stack.extend(((node.left, index), (node.right, index)))
    best = 0
    for chosen in range(1 << len(nodes)):
        if any(chosen >> a & 1 and chosen >> b & 1 for a, b in edges):
            continue
        best = max(best, sum(n.value for i, n in enumerate(nodes) if chosen >> i & 1))
    return best


def chain(values: list[int]) -> TreeNode | None:
    """A tree that is a single line, alternating left and right children."""
    root: TreeNode | None = None
    for depth, value in reversed(list(enumerate(values))):
        root = TreeNode(value, root, None) if depth % 2 else TreeNode(value, None, root)
    return root


def test_takes_the_root_and_its_grandchildren() -> None:
    """Picks nodes two levels apart when they are worth the most."""
    root = TreeNode(3, TreeNode(2, None, TreeNode(3)), TreeNode(3, None, TreeNode(1)))

    assert best_haul(root) == 7


def test_takes_both_children_of_one_node() -> None:
    """Picks two siblings, which are not joined to each other."""
    root = TreeNode(
        3, TreeNode(4, TreeNode(1), TreeNode(3)), TreeNode(5, None, TreeNode(1))
    )

    assert best_haul(root) == 9
    assert best_haul(TreeNode(1, TreeNode(6), TreeNode(7))) == 13


def test_an_empty_tree_is_worth_nothing() -> None:
    """Returns 0 for an empty tree."""
    assert best_haul(None) == 0


def test_a_single_node_is_taken() -> None:
    """Returns the value of a tree that is only a root."""
    assert best_haul(TreeNode(9)) == 9
    assert best_haul(TreeNode(0)) == 0


def test_does_not_take_a_parent_and_its_child() -> None:
    """Picks only one of two nodes joined by an edge."""
    assert best_haul(TreeNode(5, TreeNode(8))) == 8
    assert best_haul(TreeNode(8, None, TreeNode(5))) == 8


def test_may_leave_two_levels_in_a_row() -> None:
    """Skips two adjacent levels when the nodes either side are worth more.

    A chain 4, 1, 1, 4. Alternate levels give 5 either way; the answer takes
    the two ends and leaves both nodes between them.
    """
    assert best_haul(chain([4, 1, 1, 4])) == 8
    assert best_haul(chain([9, 1, 1, 9, 1, 1, 9])) == 27


def test_a_chain_behaves_like_a_row() -> None:
    """Gives the row version's answers when the tree is a single line."""
    assert best_haul(chain([2, 7, 9, 3, 1])) == 12
    assert best_haul(chain([1, 2, 3, 1])) == 4


def test_levels_are_not_all_or_nothing() -> None:
    """Takes part of one level and part of the next, on different branches.

    The left branch is best taken at its child, the right branch at its
    grandchildren.
    """
    root = TreeNode(
        1,
        TreeNode(20, TreeNode(1), TreeNode(1)),
        TreeNode(1, TreeNode(15), TreeNode(15)),
    )

    assert best_haul(root) == 50


def test_agrees_with_trying_every_set_on_every_small_tree() -> None:
    """Matches an exhaustive search for every small tree.

    Every shape of up to five nodes with every value drawn from 0, 1, 5,
    and every shape of six nodes with values 1 and 3.
    """
    for size in range(6):
        for shape in shapes(size):
            for values in product((0, 1, 5), repeat=size):
                tree = grow(shape, iter(values))
                assert best_haul(tree) == by_trying_every_set(tree), (shape, values)
    for shape in shapes(6):
        for values in product((1, 3), repeat=6):
            tree = grow(shape, iter(values))
            assert best_haul(tree) == by_trying_every_set(tree), (shape, values)


def test_leaves_the_tree_alone() -> None:
    """Does not change any node's value or children."""
    root = TreeNode(3, TreeNode(4), TreeNode(5))

    best_haul(root)

    assert (root.value, root.left.value, root.right.value) == (3, 4, 5)
    assert root.left.left is None


def test_handles_a_large_balanced_tree() -> None:
    """Handles a full tree of over eight thousand nodes, every value 1.

    Thirteen levels. The best choice is every other level starting from the
    leaves, which hold more than half of all the nodes.
    """

    def full(depth: int) -> TreeNode:
        if depth == 1:
            return TreeNode(1)
        return TreeNode(1, full(depth - 1), full(depth - 1))

    assert best_haul(full(13)) == sum(2**level for level in range(0, 13, 2))
