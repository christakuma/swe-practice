"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.

Almost everything here is a **round trip**. The format is the solver's to
choose, so the only assertable thing is the property the prompt requires:
`deserialize(serialize(tree))` is a tree identical in shape and values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from solution import TreeNode, deserialize, serialize

if TYPE_CHECKING:
    from collections.abc import Iterator


def shapes(count: int) -> list[object]:
    """Every binary tree shape with `count` nodes, as nested tuples."""
    if count == 0:
        return [None]
    out: list[object] = []
    for left_size in range(count):
        for left in shapes(left_size):
            for right in shapes(count - 1 - left_size):
                out.append((left, right))
    return out


def fill(shape: object, source: Iterator[int]) -> TreeNode | None:
    """Fill a shape with values from `source`, in pre-order."""
    if not isinstance(shape, tuple):
        return None
    node = TreeNode(next(source))
    node.left = fill(shape[0], source)
    node.right = fill(shape[1], source)
    return node


def fingerprint(root: TreeNode | None) -> object:
    """A structural fingerprint that records absent children."""
    if root is None:
        return None
    return (root.value, fingerprint(root.left), fingerprint(root.right))


def build(values: list[int | None]) -> TreeNode | None:
    """Build a tree from a level-order list, with None for a missing child."""
    if not values or values[0] is None:
        return None
    root = TreeNode(int(values[0]))
    queue = [root]
    index = 1
    while queue and index < len(values):
        node = queue.pop(0)
        for side in ("left", "right"):
            if index >= len(values):
                break
            value = values[index]
            index += 1
            if value is not None:
                child = TreeNode(int(value))
                setattr(node, side, child)
                queue.append(child)
    return root


def roundtrip(root: TreeNode | None) -> object:
    """Serialise, deserialise, and fingerprint the result."""
    return fingerprint(deserialize(serialize(root)))


def test_round_trips_a_small_tree() -> None:
    """Recovers a small tree unchanged."""
    tree = build([1, 2, 3])

    assert roundtrip(tree) == fingerprint(tree)


def test_round_trips_an_empty_tree() -> None:
    """Recovers an empty tree as an empty tree."""
    assert deserialize(serialize(None)) is None


def test_round_trips_a_single_node() -> None:
    """Recovers a one-node tree."""
    assert roundtrip(TreeNode(7)) == (7, None, None)


def test_preserves_which_side_a_lone_child_is_on() -> None:
    """Distinguishes a left-only child from a right-only one.

    The discriminating case for the whole kata. Both trees hold 1 and 2, and a
    serialisation that records only the nodes that exist produces the same
    string for both -- so the shape is unrecoverable.
    """
    left_only = build([1, 2])
    right_only = build([1, None, 2])

    assert serialize(left_only) != serialize(right_only)
    assert roundtrip(left_only) == (1, (2, None, None), None)
    assert roundtrip(right_only) == (1, None, (2, None, None))


def test_round_trips_negative_values() -> None:
    """Recovers negative values.

    A minus sign is an extra character in the token, which a fixed-width or
    single-character format mishandles.
    """
    tree = build([-1, -2, -3])

    assert roundtrip(tree) == fingerprint(tree)


def test_round_trips_multi_digit_values() -> None:
    """Recovers values of more than one digit.

    Without a delimiter between tokens, 1 followed by 2 is indistinguishable
    from 12.
    """
    tree = build([100, 2, 345])

    assert roundtrip(tree) == fingerprint(tree)
    assert roundtrip(build([12])) == (12, None, None)
    assert roundtrip(build([1, 2])) == (1, (2, None, None), None)


def test_round_trips_duplicate_values() -> None:
    """Recovers a tree whose values repeat.

    This is not a search tree, so nothing can be inferred from ordering and
    duplicates carry no information about position.
    """
    tree = build([1, 1, 1, 1, 1])

    assert roundtrip(tree) == fingerprint(tree)


def test_round_trips_zero() -> None:
    """Recovers a zero value rather than treating it as absent.

    Using a falsy value as the absence marker makes a real 0 vanish.
    """
    assert roundtrip(TreeNode(0)) == (0, None, None)
    assert roundtrip(build([0, 0, 0])) == fingerprint(build([0, 0, 0]))


def test_round_trips_a_left_chain() -> None:
    """Recovers a tree with no right children."""
    tree = build([1, 2, None, 3, None, 4])

    assert roundtrip(tree) == fingerprint(tree)


def test_round_trips_a_right_chain() -> None:
    """Recovers a tree with no left children."""
    root = TreeNode(1)
    node = root
    for value in (2, 3, 4):
        node.right = TreeNode(value)
        node = node.right

    assert roundtrip(root) == fingerprint(root)


def test_serialize_returns_a_string() -> None:
    """Returns a str from serialize and a tree or None from deserialize."""
    assert type(serialize(TreeNode(1))) is str
    assert isinstance(deserialize(serialize(TreeNode(1))), TreeNode)


def test_round_trips_every_shape_up_to_eight_nodes() -> None:
    """Recovers every binary tree shape from its own serialisation.

    Two thousand shapes -- every arrangement of up to eight nodes. A format
    that loses shape is correct on full trees and wrong on partial ones, so
    enumerating the shapes is what settles it.
    """
    for count in range(9):
        for shape in shapes(count):
            tree = fill(shape, iter(range(count)))

            assert roundtrip(tree) == fingerprint(tree), (count, shape)


def test_distinguishes_every_shape() -> None:
    """Gives every distinct small tree a distinct serialisation.

    Stated against the format directly rather than through a round trip: if
    two different trees share a string, no deserialiser can separate them, so
    the failure belongs to `serialize`.
    """
    seen: dict[str, object] = {}
    for count in range(7):
        for shape in shapes(count):
            tree = fill(shape, iter(range(count)))
            text = serialize(tree)
            structure = fingerprint(tree)

            if text in seen:
                assert seen[text] == structure, (text, seen[text], structure)
            seen[text] = structure


def test_round_trips_a_large_tree() -> None:
    """Recovers a tree of sixty thousand nodes within the time limit."""

    def balanced(low: int, high: int) -> TreeNode | None:
        if low > high:
            return None
        middle = (low + high) // 2
        return TreeNode(middle, balanced(low, middle - 1), balanced(middle + 1, high))

    tree = balanced(0, 65_534)

    assert roundtrip(tree) == fingerprint(tree)
