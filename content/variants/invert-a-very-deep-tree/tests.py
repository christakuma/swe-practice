"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator

from solution import TreeNode, invert

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


def flipped(shape: Shape) -> Shape:
    return None if shape is None else (flipped(shape[1]), flipped(shape[0]))


def layout(root: TreeNode | None) -> dict[str, int]:
    """Each node's value keyed by its path from the root, without recursing."""
    found: dict[str, int] = {}
    pending = [(root, "")]
    while pending:
        node, path = pending.pop()
        if node is not None:
            found[path] = node.value
            pending.append((node.left, path + "L"))
            pending.append((node.right, path + "R"))
    return found


def chain(depth: int, turn: str) -> tuple[TreeNode, list[TreeNode]]:
    """A chain of `depth` nodes; `turn` gives the side of each child, cycled."""
    nodes = [TreeNode(value) for value in range(depth)]
    for index in range(depth - 1):
        if turn[index % len(turn)] == "L":
            nodes[index].left = nodes[index + 1]
        else:
            nodes[index].right = nodes[index + 1]
    return nodes[0], nodes


def test_swaps_the_children_of_the_root() -> None:
    """Moves the left child to the right and the right to the left."""
    root = TreeNode(1, TreeNode(2), TreeNode(3))

    invert(root)

    assert layout(root) == {"": 1, "L": 3, "R": 2}


def test_swaps_at_every_level() -> None:
    """Mirrors the grandchildren as well as the children."""
    root = TreeNode(
        4, TreeNode(2, TreeNode(1), TreeNode(3)), TreeNode(7, TreeNode(6), TreeNode(9))
    )

    invert(root)

    assert layout(root) == {"": 4, "L": 7, "R": 2, "LL": 9, "LR": 6, "RL": 3, "RR": 1}


def test_moves_a_lone_child_to_the_other_side() -> None:
    """Moves an only child across, leaving the old side empty."""
    root = TreeNode(1, TreeNode(2))

    invert(root)

    assert root.left is None
    assert root.right is not None
    assert root.right.value == 2


def test_returns_the_same_root_and_keeps_every_node() -> None:
    """Rearranges the existing nodes rather than building new ones."""
    left, right = TreeNode(2), TreeNode(3)
    root = TreeNode(1, left, right)

    result = invert(root)

    assert result is root
    assert root.left is right
    assert root.right is left


def test_handles_an_empty_tree_and_a_single_node() -> None:
    """Returns None for no tree and the node itself for a tree of one."""
    alone = TreeNode(5)

    assert invert(None) is None
    assert invert(alone) is alone
    assert (alone.left, alone.right) == (None, None)


def test_mirrors_every_small_shape() -> None:
    """Produces the mirror image of every tree shape of up to seven nodes."""
    for size in range(8):
        for shape in shapes(size):
            tree = grow(shape, iter(range(size)))
            expected = {
                path.translate(str.maketrans("LR", "RL")): value
                for path, value in layout(tree).items()
            }
            assert layout(invert(tree)) == expected, shape
            assert expected == layout(grow(flipped(shape), iter(_mirror_order(shape))))


def _mirror_order(shape: Shape) -> list[int]:
    """Pre-order values of `shape`, read off in the mirrored tree's pre-order."""
    labelled = grow(shape, iter(range(10**6)))
    order: list[int] = []
    pending = [labelled]
    while pending:
        node = pending.pop()
        if node is not None:
            order.append(node.value)
            pending.append(node.left)
            pending.append(node.right)
    return order


def test_inverting_twice_restores_the_tree() -> None:
    """Returns every node to where it started when applied twice."""
    root = TreeNode(1, TreeNode(2, None, TreeNode(4)), TreeNode(3))
    before = layout(root)

    invert(invert(root))

    assert layout(root) == before


def test_inverts_a_chain_a_hundred_thousand_deep() -> None:
    """Turns a left-leaning chain of 100,000 nodes into a right-leaning one.

    Every node has one child, so the tree is as deep as it has nodes. A
    function that calls itself once per level stops at about the thousandth.
    """
    root, nodes = chain(100_000, "L")

    assert invert(root) is root

    for index in range(len(nodes) - 1):
        assert nodes[index].left is None
        assert nodes[index].right is nodes[index + 1]


def test_inverts_a_deep_zigzag() -> None:
    """Swaps every turn of a 100,000-node chain that alternates sides."""
    root, nodes = chain(100_000, "LLR")

    invert(root)

    for index in range(len(nodes) - 1):
        went_left = "LLR"[index % 3] == "L"
        mirrored = nodes[index].right if went_left else nodes[index].left
        emptied = nodes[index].left if went_left else nodes[index].right
        assert mirrored is nodes[index + 1], index
        assert emptied is None, index


def test_inverts_a_deep_chain_with_branches_off_it() -> None:
    """Reaches the small subtrees hanging off a very deep spine."""
    root, nodes = chain(50_000, "R")
    for index in range(0, 50_000, 1000):
        nodes[index].left = TreeNode(-index, TreeNode(-index - 1), None)

    invert(root)

    for index in range(0, 50_000, 1000):
        twig = nodes[index].right
        assert twig is not None
        assert twig.value == -index
        assert twig.left is None
        assert twig.right is not None
        assert twig.right.value == -index - 1
    assert nodes[49_998].left is nodes[49_999]
