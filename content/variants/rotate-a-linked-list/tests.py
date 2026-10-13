"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise

from solution import ListNode, rotate


def build(values: list[int]) -> list[ListNode]:
    nodes = [ListNode(value) for value in values]
    for node, following in pairwise(nodes):
        node.next_node = following
    return nodes


def walk(head: ListNode | None, limit: int = 100_000) -> list[ListNode]:
    """The nodes from `head` on, failing rather than looping if it never ends."""
    found = []
    while head is not None:
        found.append(head)
        assert len(found) <= limit, "the list does not end"
        head = head.next_node
    return found


def rotated(values: list[int], k: int) -> list[int]:
    nodes = build(values)
    return [node.value for node in walk(rotate(nodes[0] if nodes else None, k))]


def test_moves_the_last_nodes_to_the_front() -> None:
    """Rotates a list by fewer places than its length."""
    assert rotated([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]
    assert rotated([1, 2, 3, 4, 5], 1) == [5, 1, 2, 3, 4]
    assert rotated([1, 2, 3, 4, 5], 4) == [2, 3, 4, 5, 1]


def test_rotating_by_zero_changes_nothing() -> None:
    """Returns the list as it was for k = 0."""
    assert rotated([1, 2, 3], 0) == [1, 2, 3]


def test_rotating_by_the_length_changes_nothing() -> None:
    """Returns the list as it was after one full turn, or several."""
    assert rotated([1, 2, 3], 3) == [1, 2, 3]
    assert rotated([1, 2, 3], 9) == [1, 2, 3]


def test_k_may_exceed_the_length() -> None:
    """Rotates by the remainder when k is larger than the list."""
    assert rotated([0, 1, 2], 4) == [2, 0, 1]
    assert rotated([1, 2, 3, 4, 5], 12) == [4, 5, 1, 2, 3]


def test_handles_an_enormous_k() -> None:
    """Rotates by a thousand million places without walking that far."""
    assert rotated([1, 2, 3, 4, 5, 6, 7], 10**9) == rotated(
        [1, 2, 3, 4, 5, 6, 7], 10**9 % 7
    )
    assert rotated([1, 2, 3, 4, 5, 6, 7], 10**9) == [2, 3, 4, 5, 6, 7, 1]


def test_handles_an_empty_list_and_a_single_node() -> None:
    """Returns None for no list, and the node itself for a list of one."""
    alone = ListNode(5)

    assert rotate(None, 3) is None
    assert rotate(None, 0) is None
    assert rotate(alone, 7) is alone
    assert alone.next_node is None


def test_reuses_the_nodes_it_was_given() -> None:
    """Relinks the original nodes rather than creating new ones."""
    nodes = build([1, 2, 3, 4, 5])

    result = walk(rotate(nodes[0], 2))

    assert [id(node) for node in result] == [id(nodes[i]) for i in (3, 4, 0, 1, 2)]


def test_the_result_ends() -> None:
    """Leaves the new last node pointing at nothing."""
    nodes = build([1, 2, 3])

    result = walk(rotate(nodes[0], 1))

    assert result[-1] is nodes[1]
    assert nodes[1].next_node is None


def test_agrees_with_slicing_for_every_short_list() -> None:
    """Matches a slice-and-join for every length up to 8 and every k up to 20."""
    for length in range(1, 9):
        values = list(range(length))
        for k in range(21):
            cut = length - k % length
            assert rotated(values, k) == values[cut:] + values[:cut], (length, k)


def test_handles_repeated_values() -> None:
    """Rotates by position when the values do not tell the nodes apart."""
    assert rotated([7, 7, 8, 7], 1) == [7, 7, 7, 8]


def test_rotates_a_long_list() -> None:
    """Rotates twenty thousand nodes."""
    size = 20_000
    values = list(range(size))

    assert rotated(values, 5_000) == values[15_000:] + values[:15_000]
    assert rotated(values, 3 * size + 1) == [size - 1, *values[:-1]]
