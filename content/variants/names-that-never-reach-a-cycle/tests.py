"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import safe_names

NAMES = ("a", "b", "c")


def by_reachability(graph: dict[str, list[str]]) -> list[str]:
    """Work out who can reach whom, and call a name unsafe if it reaches a loop."""
    names = set(graph) | {other for needed in graph.values() for other in needed}
    reach = {name: set(graph.get(name, ())) for name in names}
    for _ in names:
        for name in names:
            for other in list(reach[name]):
                reach[name] |= reach[other]
    looping = {name for name in names if name in reach[name]}
    return sorted(
        name for name in names if name not in looping and not reach[name] & looping
    )


def test_everything_is_safe_without_a_cycle() -> None:
    """Returns every name when nothing loops."""
    assert safe_names({"a": ["b"], "b": ["c"], "c": []}) == ["a", "b", "c"]


def test_excludes_a_cycle_and_whatever_depends_on_it() -> None:
    """Excludes names on a cycle and names that lead into one."""
    graph = {"app": ["lib"], "lib": ["core"], "core": ["lib"], "tool": ["util"]}

    assert safe_names(graph) == ["tool", "util"]


def test_includes_names_that_are_only_dependencies() -> None:
    """Counts a name with no entry of its own as safe."""
    assert safe_names({"a": ["b", "c"]}) == ["a", "b", "c"]


def test_a_name_depending_on_itself_is_unsafe() -> None:
    """Treats a self-dependency as a cycle."""
    assert safe_names({"x": ["x"]}) == []
    assert safe_names({"x": ["x"], "y": []}) == ["y"]


def test_one_bad_dependency_among_good_ones_is_enough() -> None:
    """Excludes a name with one unsafe dependency and several safe ones."""
    graph = {"a": ["ok", "bad"], "ok": [], "bad": ["bad"]}

    assert safe_names(graph) == ["ok"]


def test_handles_an_empty_graph_and_repeated_dependencies() -> None:
    """Returns nothing for nothing, and is not confused by a repeated dependency."""
    assert safe_names({}) == []
    assert safe_names({"a": ["b", "b"]}) == ["a", "b"]


def test_agrees_with_reachability_for_every_small_graph() -> None:
    """Matches a reachability check for every graph on three names."""
    for bits in product((0, 1), repeat=9):
        graph = {
            name: [
                other for column, other in enumerate(NAMES) if bits[row * 3 + column]
            ]
            for row, name in enumerate(NAMES)
        }
        assert safe_names(graph) == by_reachability(graph), graph


def test_follows_a_chain_far_deeper_than_python_will_recurse() -> None:
    """Handles a chain ten thousand deep, with and without a loop at the end."""
    depth = 10_000
    chain = {f"n{index:05d}": [f"n{index + 1:05d}"] for index in range(depth)}

    assert len(safe_names(chain)) == depth + 1

    chain[f"n{depth:05d}"] = [f"n{depth:05d}"]

    assert safe_names(chain) == []
