"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import build_rounds

NAMES = ("a", "b", "c")


def by_depth(graph: dict[str, list[str]]) -> list[list[str]] | None:
    """A name's round is one more than the latest round among what it needs."""
    names = sorted(
        set(graph) | {other for needed in graph.values() for other in needed}
    )
    depth: dict[str, int] = {}
    for _ in range(len(names) + 1):
        for name in names:
            needed = graph.get(name, [])
            if all(other in depth for other in needed):
                depth[name] = 1 + max((depth[other] for other in needed), default=-1)
    if len(depth) != len(names):
        return None
    return [
        [name for name in names if depth[name] == level]
        for level in range(max(depth.values(), default=-1) + 1)
    ]


def test_groups_the_documented_graph() -> None:
    """Puts each name in the earliest round it can be in."""
    graph = {"app": ["lib", "log"], "lib": ["core"], "log": [], "core": []}

    assert build_rounds(graph) == [["core", "log"], ["lib"], ["app"]]


def test_places_a_name_that_is_only_a_dependency() -> None:
    """Puts a name with no entry of its own in the first round."""
    assert build_rounds({"build": ["tools"]}) == [["tools"], ["build"]]


def test_returns_none_for_a_cycle() -> None:
    """Returns None when there is a cycle, however much else is fine."""
    assert build_rounds({"a": ["b"], "b": ["a"]}) is None
    assert build_rounds({"ok": [], "a": ["ok", "b"], "b": ["a"]}) is None
    assert build_rounds({"x": ["x"]}) is None


def test_returns_no_rounds_for_no_names() -> None:
    """Returns an empty list for an empty graph."""
    assert build_rounds({}) == []


def test_waits_for_the_slowest_dependency() -> None:
    """Places a name after its latest dependency, not its earliest."""
    graph = {"top": ["quick", "slow"], "slow": ["mid"], "mid": ["base"]}

    assert build_rounds(graph) == [["base", "quick"], ["mid"], ["slow"], ["top"]]


def test_sorts_within_a_round() -> None:
    """Sorts each round ascending, whatever order the names arrived in."""
    assert build_rounds({"z": [], "m": [], "a": []}) == [["a", "m", "z"]]


def test_agrees_with_depths_for_every_small_graph() -> None:
    """Matches a depth calculation for every graph on three names."""
    for bits in product((0, 1), repeat=9):
        graph = {
            name: [
                other for column, other in enumerate(NAMES) if bits[row * 3 + column]
            ]
            for row, name in enumerate(NAMES)
        }
        assert build_rounds(graph) == by_depth(graph), graph


def test_handles_a_deep_chain_and_a_wide_fan() -> None:
    """Handles ten thousand rounds of one, and one round of ten thousand."""
    size = 10_000
    chain = {f"n{index:05d}": [f"n{index + 1:05d}"] for index in range(size)}
    fan = {f"n{index:05d}": ["root"] for index in range(size)}

    rounds = build_rounds(chain)
    assert rounds is not None
    assert len(rounds) == size + 1
    assert rounds[0] == [f"n{size:05d}"]

    wide = build_rounds(fan)
    assert wide is not None
    assert [len(group) for group in wide] == [1, size]
