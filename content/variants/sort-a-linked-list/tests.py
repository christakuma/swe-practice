"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from itertools import pairwise, permutations, product

from solution import ListNode, sort_list


def build(values: list[int]) -> list[ListNode]:
    nodes = [ListNode(value) for value in values]
    for node, following in pairwise(nodes):
        node.next = following
    return nodes


def walk(head: ListNode | None, limit: int = 200_000) -> list[ListNode]:
    """The nodes from `head` on, failing rather than looping if it never ends."""
    found = []
    while head is not None:
        found.append(head)
        if len(found) > limit:
            raise AssertionError("the list does not terminate -- it is cyclic")
        head = head.next
    return found


def jumbled(size: int, stride: int) -> list[int]:
    """The values 0 to `size - 1` in a fixed scrambled order.

    Stepping through them `stride` at a time visits each once, as long as
    the two share no factor.
    """
    return [position * stride % size for position in range(size)]


def sort_values(values: list[int]) -> list[int]:
    nodes = build(values)
    return [node.value for node in walk(sort_list(nodes[0] if nodes else None))]


def test_sorts_a_short_list() -> None:
    """Returns the values in ascending order."""
    assert sort_values([4, 2, 1, 3]) == [1, 2, 3, 4]
    assert sort_values([-1, 5, 3, 4, 0]) == [-1, 0, 3, 4, 5]


def test_handles_an_empty_list_and_a_single_node() -> None:
    """Returns None for no list and the node itself for a list of one."""
    alone = ListNode(5)

    assert sort_list(None) is None
    assert sort_list(alone) is alone
    assert alone.next is None


def test_sorts_two_nodes() -> None:
    """Swaps two nodes that are out of order and leaves two that are not."""
    assert sort_values([2, 1]) == [1, 2]
    assert sort_values([1, 2]) == [1, 2]


def test_leaves_a_sorted_list_sorted() -> None:
    """Returns an already ascending list unchanged."""
    assert sort_values([1, 2, 3, 4, 5, 6]) == [1, 2, 3, 4, 5, 6]


def test_sorts_a_reversed_list() -> None:
    """Reverses a descending list."""
    assert sort_values([6, 5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5, 6]
    assert sort_values([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]


def test_handles_repeated_and_negative_values() -> None:
    """Sorts values that repeat and values below zero."""
    assert sort_values([3, -1, 3, 0, -1, 3]) == [-1, -1, 0, 3, 3, 3]
    assert sort_values([7, 7, 7]) == [7, 7, 7]


def test_returns_the_original_nodes_each_with_its_own_value() -> None:
    """Relinks the nodes it was given and moves no values between them."""
    nodes = build([30, 10, 40, 20])

    result = walk(sort_list(nodes[0]))

    assert [id(node) for node in result] == [id(nodes[i]) for i in (1, 3, 0, 2)]
    assert [node.value for node in nodes] == [30, 10, 40, 20]


def test_equal_values_keep_their_original_order() -> None:
    """Sorts stably: nodes with the same value come out in the order they went in."""
    nodes = build([2, 1, 2, 1, 2])

    result = walk(sort_list(nodes[0]))

    assert [id(node) for node in result] == [id(nodes[i]) for i in (1, 3, 0, 2, 4)]


def test_the_last_node_points_at_nothing() -> None:
    """Ends the list at its largest node.

    The largest node was somewhere in the middle and still points at
    whatever followed it unless told otherwise.
    """
    nodes = build([9, 1, 5])

    result = walk(sort_list(nodes[0]))

    assert result[-1] is nodes[0]
    assert nodes[0].next is None


def test_sorts_every_arrangement_of_a_short_list() -> None:
    """Sorts every ordering of up to seven distinct values."""
    for size in range(8):
        for values in permutations(range(size)):
            assert sort_values(list(values)) == list(range(size)), values


def test_sorts_stably_for_every_short_list_with_repeats() -> None:
    """Matches a stable sort, node for node, on every short list with repeats.

    Every list of up to six values drawn from three.
    """
    for size in range(7):
        for values in product(range(3), repeat=size):
            nodes = build(list(values))
            expected = sorted(nodes, key=lambda node: node.value)

            result = walk(sort_list(nodes[0] if nodes else None))

            assert [id(node) for node in result] == [id(node) for node in expected], (
                values
            )


def test_sorts_fifty_thousand_nodes_in_shuffled_order() -> None:
    """Sorts fifty thousand jumbled nodes within the time limit.

    A sort that inserts each node into place by walking from the head takes
    hundreds of millions of steps on this.
    """
    size = 50_000
    values = jumbled(size, 7_919)

    assert sorted(values) == list(range(size))
    assert sort_values(values) == list(range(size))


def test_sorts_long_lists_that_are_already_in_order_or_reversed() -> None:
    """Sorts fifty thousand nodes that start ascending, and that start descending."""
    size = 50_000

    assert sort_values(list(range(size))) == list(range(size))
    assert sort_values(list(range(size, 0, -1))) == list(range(1, size + 1))


def test_sorts_without_collecting_the_nodes() -> None:
    """Sorts fifty thousand nodes while allocating almost nothing.

    A Python list holding every node is 400,000 bytes before anything is
    done with it. Relinking needs a handful of names and a few frames.
    """
    size = 50_000
    nodes = build(jumbled(size, 3_331))

    tracemalloc.start()
    head = sort_list(nodes[0])
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 64_000, f"allocated {peak} bytes"
    assert [node.value for node in walk(head)] == list(range(size))
