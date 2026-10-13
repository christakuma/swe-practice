"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise

from solution import ListNode, reverse_in_groups


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


def regrouped(values: list[int], k: int) -> list[int]:
    nodes = build(values)
    return [
        node.value for node in walk(reverse_in_groups(nodes[0] if nodes else None, k))
    ]


def by_slicing(values: list[int], k: int) -> list[int]:
    result: list[int] = []
    for start in range(0, len(values), k):
        group = values[start : start + k]
        result.extend(reversed(group) if len(group) == k else group)
    return result


def test_swaps_pairs() -> None:
    """Reverses each pair for k = 2."""
    assert regrouped([1, 2, 3, 4], 2) == [2, 1, 4, 3]


def test_reverses_groups_of_three() -> None:
    """Reverses each full group of three."""
    assert regrouped([1, 2, 3, 4, 5, 6], 3) == [3, 2, 1, 6, 5, 4]


def test_leaves_a_short_final_group_alone() -> None:
    """Keeps the order of leftover nodes that do not make a full group."""
    assert regrouped([1, 2, 3, 4, 5], 2) == [2, 1, 4, 3, 5]
    assert regrouped([1, 2, 3, 4, 5], 3) == [3, 2, 1, 4, 5]
    assert regrouped([1, 2, 3, 4, 5, 6, 7, 8], 3) == [3, 2, 1, 6, 5, 4, 7, 8]


def test_a_group_size_of_one_changes_nothing() -> None:
    """Returns the list as it was for k = 1."""
    assert regrouped([1, 2, 3], 1) == [1, 2, 3]


def test_a_group_as_long_as_the_list_reverses_all_of_it() -> None:
    """Reverses the whole list when k equals its length."""
    assert regrouped([1, 2, 3, 4], 4) == [4, 3, 2, 1]


def test_a_group_longer_than_the_list_changes_nothing() -> None:
    """Returns the list as it was when there is not one full group."""
    assert regrouped([1, 2], 5) == [1, 2]
    assert regrouped([1, 2, 3], 4) == [1, 2, 3]


def test_handles_an_empty_list_and_a_single_node() -> None:
    """Returns None for no list and the node itself for a list of one."""
    alone = ListNode(5)

    assert reverse_in_groups(None, 2) is None
    assert reverse_in_groups(alone, 1) is alone
    assert reverse_in_groups(alone, 3) is alone


def test_relinks_the_nodes_without_moving_values() -> None:
    """Returns the original nodes in a new order, each still holding its own value."""
    nodes = build([10, 20, 30, 40, 50])

    result = walk(reverse_in_groups(nodes[0], 2))

    assert [id(node) for node in result] == [id(nodes[i]) for i in (1, 0, 3, 2, 4)]
    assert [node.value for node in nodes] == [10, 20, 30, 40, 50]


def test_the_groups_are_joined_to_each_other() -> None:
    """Links the end of each reversed group to the start of the next.

    After reversing, node 1 is the last of the first group and must point at
    node 6, the new first of the second -- not at node 4, where the second
    group used to begin.
    """
    nodes = build([1, 2, 3, 4, 5, 6])

    reverse_in_groups(nodes[0], 3)

    assert nodes[0].next_node is nodes[5]
    assert nodes[3].next_node is None


def test_agrees_with_slicing_for_every_short_list() -> None:
    """Matches a slice-and-reverse for every length up to 12 and every k up to 13."""
    for length in range(13):
        values = list(range(length))
        for k in range(1, 14):
            assert regrouped(values, k) == by_slicing(values, k), (length, k)


def test_handles_many_small_groups_without_recursing() -> None:
    """Reverses thirty thousand nodes in pairs, which is fifteen thousand groups.

    One function call per group is fifteen thousand nested calls.
    """
    values = list(range(30_000))

    assert regrouped(values, 2) == by_slicing(values, 2)
    assert regrouped(values, 1) == values


def test_handles_a_few_large_groups() -> None:
    """Reverses thirty thousand nodes in groups of seven thousand."""
    values = list(range(30_000))

    assert regrouped(values, 7_000) == by_slicing(values, 7_000)
