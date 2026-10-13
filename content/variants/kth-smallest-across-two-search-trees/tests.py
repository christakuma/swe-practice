"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import TreeNode, kth_smallest


def balanced(values: list[int]) -> TreeNode | None:
    """A balanced BST over sorted values."""
    if not values:
        return None
    middle = len(values) // 2
    return TreeNode(
        values[middle], balanced(values[:middle]), balanced(values[middle + 1 :])
    )


class Landmine(TreeNode):
    """A node that refuses to be looked at.

    The only way to check an *early exit* from the outside: a tree cannot tell
    you how much of it was read, but a node that raises on access can. Planted
    where a correct solution has no reason to go.
    """

    def __init__(self) -> None:
        """Deliberately uninitialised -- every attribute access raises."""

    @property
    def value(self) -> int:
        raise AssertionError("read a node the answer did not require")

    @property
    def left(self) -> TreeNode | None:
        raise AssertionError("descended past the answer")

    @property
    def right(self) -> TreeNode | None:
        raise AssertionError("descended past the answer")


def test_merges_the_two_orders() -> None:
    """Returns the values of both trees in one ascending sequence."""
    first = TreeNode(2, TreeNode(1), TreeNode(4))
    second = TreeNode(3, None, TreeNode(6))

    assert [kth_smallest(first, second, k) for k in range(1, 6)] == [1, 2, 3, 4, 6]


def test_a_value_in_both_trees_counts_twice() -> None:
    """Gives a shared value two consecutive places in the order."""
    first = TreeNode(5, TreeNode(3))
    second = TreeNode(5, None, TreeNode(8))

    assert [kth_smallest(first, second, k) for k in range(1, 5)] == [3, 5, 5, 8]
    assert [kth_smallest(TreeNode(1), TreeNode(1), k) for k in (1, 2)] == [1, 1]


def test_one_tree_may_be_empty() -> None:
    """Answers from the other tree alone when one is None."""
    tree = TreeNode(7, TreeNode(2), TreeNode(9))

    assert [kth_smallest(None, tree, k) for k in (1, 2, 3)] == [2, 7, 9]
    assert [kth_smallest(tree, None, k) for k in (1, 2, 3)] == [2, 7, 9]


def test_one_tree_entirely_below_the_other() -> None:
    """Exhausts one tree before taking anything from the other."""
    low, high = balanced([1, 2, 3]), balanced([10, 20, 30])

    assert [kth_smallest(low, high, k) for k in range(1, 7)] == [1, 2, 3, 10, 20, 30]
    assert [kth_smallest(high, low, k) for k in range(1, 7)] == [1, 2, 3, 10, 20, 30]


def test_handles_negative_values_and_chains() -> None:
    """Handles trees that lean entirely one way and values below zero."""
    rising = TreeNode(-5, None, TreeNode(0, None, TreeNode(5)))
    falling = TreeNode(4, TreeNode(-1, TreeNode(-9)))

    assert [kth_smallest(rising, falling, k) for k in range(1, 7)] == [
        -9,
        -5,
        -1,
        0,
        4,
        5,
    ]


def test_agrees_with_sorting_everything() -> None:
    """Matches a sort of all the values, for every k, for many pairs of trees.

    Every pair of subsets of 0..5 as the two trees' values, shared values
    included.
    """
    subsets = [
        list(chosen) for size in range(7) for chosen in combinations(range(6), size)
    ]
    for first_values in subsets[::3]:
        for second_values in subsets[::2]:
            everything = sorted(first_values + second_values)
            first, second = balanced(first_values), balanced(second_values)
            for k in range(1, len(everything) + 1):
                assert kth_smallest(first, second, k) == everything[k - 1], (
                    first_values,
                    second_values,
                    k,
                )


def test_leaves_both_trees_alone() -> None:
    """Does not modify either tree."""
    first, second = balanced([1, 3, 5]), balanced([2, 4])

    kth_smallest(first, second, 4)

    assert (first.value, first.left.value, first.right.value) == (3, 1, 5)
    assert (second.value, second.left.value, second.right) == (4, 2, None)


def test_stops_as_soon_as_it_has_the_answer() -> None:
    """Does not read on through either tree once it has the kth value.

    Each tree has a few small values on the left of its root, and a landmine
    two nodes further along its ascending order than the root is. The six
    smallest values are all in the small parts. Flattening both trees first
    trips a landmine, whether the walk recurses or keeps a stack of its own.

    The landmines stand well back on purpose: a merge may fairly look a
    value or two ahead in each tree before it knows which comes next, and
    that is not the mistake being tested for.
    """

    def guarded(root_value: int, small: list[int]) -> TreeNode:
        beyond = TreeNode(root_value + 1, None, Landmine())
        return TreeNode(root_value, balanced(small), beyond)

    first = guarded(1000, [1, 4, 7])
    second = guarded(2000, [2, 3, 9])

    assert [kth_smallest(first, second, k) for k in range(1, 7)] == [
        1,
        2,
        3,
        4,
        7,
        9,
    ]


def test_answers_beside_branches_too_deep_to_recurse_down() -> None:
    """Answers small k beside a branch 100,000 nodes deep in each tree.

    Each tree has a few small values on the left of its root and a chain of
    large values on the right. The six smallest values are all in the small
    parts, so nothing on either chain needs visiting. A recursive walk that
    collects every value first runs out of stack going down a chain. That is
    all this test can say: a walk that carries its own stack gets to the
    bottom, and the landmines above are what catch it.
    """

    def with_a_deep_right(root_value: int, small: list[int]) -> TreeNode:
        chain = TreeNode(root_value + 1)
        node = chain
        for value in range(root_value + 2, root_value + 100_001):
            node.right = TreeNode(value)
            node = node.right
        return TreeNode(root_value, balanced(small), chain)

    first = with_a_deep_right(1000, [1, 4, 7])
    second = with_a_deep_right(2000, [2, 3, 9])

    assert [kth_smallest(first, second, k) for k in range(1, 8)] == [
        1,
        2,
        3,
        4,
        7,
        9,
        1000,
    ]


def test_finds_values_in_two_large_trees() -> None:
    """Finds values across two balanced trees of fifty thousand nodes each."""
    evens = balanced(list(range(0, 100_000, 2)))
    odds = balanced(list(range(1, 100_000, 2)))

    assert kth_smallest(evens, odds, 1) == 0
    assert kth_smallest(evens, odds, 2) == 1
    assert kth_smallest(evens, odds, 100_000) == 99_999
    assert kth_smallest(evens, odds, 31_416) == 31_415
