"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator
from itertools import product

from solution import TreeNode, is_same_tree

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


def canonical(node: TreeNode | None) -> object:
    """A form that is equal for two trees exactly when swaps relate them."""
    if node is None:
        return ()
    return (
        node.value,
        *sorted([repr(canonical(node.left)), repr(canonical(node.right))]),
    )


def test_identical_trees_need_no_swaps() -> None:
    """Accepts two trees that are already the same."""
    first = TreeNode(1, TreeNode(2), TreeNode(3))
    second = TreeNode(1, TreeNode(2), TreeNode(3))

    assert is_same_tree(first, second)


def test_accepts_a_swap_at_the_root() -> None:
    """Accepts trees that differ by one swap at the root."""
    first = TreeNode(1, TreeNode(2), TreeNode(3))
    second = TreeNode(1, TreeNode(3), TreeNode(2))

    assert is_same_tree(first, second)


def test_accepts_a_swap_at_some_nodes_and_not_others() -> None:
    """Accepts a swap at the root with the subtree below left as it was."""
    first = TreeNode(1, TreeNode(2, TreeNode(4), TreeNode(5)), TreeNode(3))
    second = TreeNode(1, TreeNode(3), TreeNode(2, TreeNode(4), TreeNode(5)))
    deeper = TreeNode(1, TreeNode(2, TreeNode(5), TreeNode(4)), TreeNode(3))

    assert is_same_tree(first, second)
    assert is_same_tree(first, deeper)


def test_accepts_a_lone_child_on_either_side() -> None:
    """Treats a single left child and a single right child as one swap apart."""
    assert is_same_tree(TreeNode(1, TreeNode(2)), TreeNode(1, None, TreeNode(2)))


def test_rejects_different_values() -> None:
    """Rejects trees whose values cannot be lined up by any swaps."""
    first = TreeNode(1, TreeNode(2), TreeNode(3))

    assert not is_same_tree(first, TreeNode(1, TreeNode(2), TreeNode(4)))
    assert not is_same_tree(first, TreeNode(9, TreeNode(2), TreeNode(3)))


def test_rejects_a_value_that_moved_to_another_parent() -> None:
    """Rejects a tree where a node sits under a different parent."""
    first = TreeNode(1, TreeNode(2, TreeNode(4)), TreeNode(3))
    second = TreeNode(1, TreeNode(2), TreeNode(3, TreeNode(4)))

    assert not is_same_tree(first, second)


def test_does_not_match_one_child_twice() -> None:
    """Rejects a pairing that uses one of the second tree's children twice."""
    first = TreeNode(1, TreeNode(2), TreeNode(2))
    second = TreeNode(1, TreeNode(2), TreeNode(3))

    assert not is_same_tree(first, second)
    assert not is_same_tree(second, first)


def test_handles_empty_trees() -> None:
    """Calls two empty trees the same and an empty and a non-empty one different."""
    assert is_same_tree(None, None)
    assert not is_same_tree(None, TreeNode(1))
    assert not is_same_tree(TreeNode(1), None)


def test_agrees_with_a_canonical_form_on_every_small_pair() -> None:
    """Matches a sorted canonical form for every pair of small trees.

    Every tree of up to four nodes with each value 1 or 2, against every
    other.
    """
    trees = [
        grow(shape, iter(values))
        for size in range(5)
        for shape in shapes(size)
        for values in product((1, 2), repeat=size)
    ]
    forms = [repr(canonical(tree)) for tree in trees]
    matches = 0
    for first, first_form in zip(trees, forms, strict=True):
        for second, second_form in zip(trees, forms, strict=True):
            expected = first_form == second_form
            assert is_same_tree(first, second) == expected, (first_form, second_form)
            matches += expected
    assert matches > len(trees)


def test_leaves_both_trees_as_they_were() -> None:
    """Does not actually perform the swaps it considers."""
    first = TreeNode(1, TreeNode(2), TreeNode(3))
    second = TreeNode(1, TreeNode(3), TreeNode(2))

    is_same_tree(first, second)

    assert (first.left.value, first.right.value) == (2, 3)
    assert (second.left.value, second.right.value) == (3, 2)
