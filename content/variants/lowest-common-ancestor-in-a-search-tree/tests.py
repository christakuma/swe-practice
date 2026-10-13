"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import permutations

from solution import TreeNode, lowest_common_ancestor


def grown(order: tuple[int, ...]) -> TreeNode:
    """A search tree made by inserting the values in the order given."""
    root = TreeNode(order[0])
    for value in order[1:]:
        node = root
        while True:
            if value < node.value:
                if node.left is None:
                    node.left = TreeNode(value)
                    break
                node = node.left
            else:
                if node.right is None:
                    node.right = TreeNode(value)
                    break
                node = node.right
    return root


def path_to(root: TreeNode, value: int) -> list[int]:
    """The values from the root down to `value`."""
    path = []
    node: TreeNode | None = root
    while node is not None:
        path.append(node.value)
        if value == node.value:
            break
        node = node.left if value < node.value else node.right
    return path


def last_shared(first: list[int], second: list[int]) -> int:
    shared = [a for a, b in zip(first, second, strict=False) if a == b]
    return shared[-1]


class Landmine(TreeNode):
    """A node that refuses to be looked at.

    The only way to check from the outside that a subtree was *not entered*: a
    tree cannot tell you how much of it was read, but a node that raises on
    access can. Planted on the side of a node that a walk guided by the
    ordering has no reason to take.
    """

    def __init__(self) -> None:
        """Deliberately uninitialised -- every attribute access raises."""

    @property
    def value(self) -> int:
        raise AssertionError("read a node the answer did not require")

    @property
    def left(self) -> TreeNode | None:
        raise AssertionError("entered a subtree the answer is not in")

    @property
    def right(self) -> TreeNode | None:
        raise AssertionError("entered a subtree the answer is not in")


def example() -> TreeNode:
    return grown((6, 2, 8, 0, 4, 7, 9, 3, 5))


def test_finds_the_root_for_values_on_opposite_sides() -> None:
    """Returns the root when the values straddle it."""
    assert lowest_common_ancestor(example(), 2, 8) == 6


def test_finds_an_ancestor_below_the_root() -> None:
    """Returns the deepest common ancestor, not the root."""
    assert lowest_common_ancestor(example(), 3, 5) == 4
    assert lowest_common_ancestor(example(), 7, 9) == 8


def test_a_node_is_its_own_ancestor() -> None:
    """Returns the upper value when one is above the other."""
    assert lowest_common_ancestor(example(), 2, 4) == 2
    assert lowest_common_ancestor(example(), 5, 2) == 2
    assert lowest_common_ancestor(example(), 9, 9) == 9


def test_does_not_depend_on_the_order_of_the_two_values() -> None:
    """Gives the same answer whichever way round the values are given."""
    assert lowest_common_ancestor(example(), 8, 2) == 6
    assert lowest_common_ancestor(example(), 5, 3) == 4


def test_agrees_with_comparing_paths_for_every_small_tree() -> None:
    """Matches the last shared node of the two paths, for every tree of five."""
    for order in permutations(range(5)):
        tree = grown(order)
        for first in range(5):
            for second in range(5):
                expected = last_shared(path_to(tree, first), path_to(tree, second))
                assert lowest_common_ancestor(tree, first, second) == expected


def test_does_not_enter_a_subtree_the_answer_is_not_in() -> None:
    """Never reads a node on the side of the tree the values are not on.

    Both values are on one side of the root, and the root's other child is a
    landmine. A search of the whole tree has to look at it, whether it
    recurses or keeps a stack of its own; a walk guided by the ordering never
    goes that way.
    """
    right = TreeNode(800, TreeNode(700), TreeNode(900))
    leaning_right = TreeNode(500, Landmine(), right)

    assert lowest_common_ancestor(leaning_right, 700, 900) == 800
    assert lowest_common_ancestor(leaning_right, 900, 500) == 500

    left = TreeNode(200, TreeNode(100), TreeNode(300))
    leaning_left = TreeNode(500, left, Landmine())

    assert lowest_common_ancestor(leaning_left, 100, 300) == 200
    assert lowest_common_ancestor(leaning_left, 500, 100) == 500


def test_answers_beside_a_chain_too_deep_to_recurse_down() -> None:
    """Answers beside a chain 100,000 deep.

    Both values are on the right of the root and the chain hangs on the
    left. A recursive search of the whole tree runs out of stack going down
    it. That is all this test can say: a search that carries its own stack
    gets to the bottom, and the landmine above is what catches it.
    """
    middle = 500_000
    chain = TreeNode(middle - 1)
    node = chain
    for value in range(middle - 2, middle - 100_001, -1):
        node.left = TreeNode(value)
        node = node.left
    right = TreeNode(800_000, TreeNode(700_000), TreeNode(900_000))
    root = TreeNode(middle, chain, right)

    assert lowest_common_ancestor(root, 700_000, 900_000) == 800_000
    assert lowest_common_ancestor(root, 900_000, middle) == middle
