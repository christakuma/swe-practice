"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import find_cycle

type Graph = dict[str, list[str]]


def is_cycle(dependencies: Graph, names: list[str] | None) -> bool:
    """Whether `names` is a real cycle: distinct, and each depends on the next."""
    if not names or len(set(names)) != len(names):
        return False
    return all(
        following in dependencies.get(name, ())
        for name, following in zip(names, names[1:] + names[:1], strict=True)
    )


def has_cycle(dependencies: Graph) -> bool:
    """Whether a cycle exists, by repeatedly removing names with nothing left."""
    remaining = {name: set(needs) for name, needs in dependencies.items()}
    for needs in dependencies.values():
        for name in needs:
            remaining.setdefault(name, set())
    while True:
        free = [name for name, needs in remaining.items() if not needs]
        if not free:
            return bool(remaining)
        for name in free:
            del remaining[name]
        for needs in remaining.values():
            needs.difference_update(free)


def test_returns_a_simple_cycle() -> None:
    """Returns the three names of a three-name cycle."""
    graph = {"a": ["b"], "b": ["c"], "c": ["a"]}

    found = find_cycle(graph)

    assert is_cycle(graph, found)
    assert sorted(found or []) == ["a", "b", "c"]


def test_returns_none_when_nothing_leads_back() -> None:
    """Returns None for a chain, a tree and an empty graph."""
    assert find_cycle({}) is None
    assert find_cycle({"a": ["b"], "b": ["c"]}) is None
    assert find_cycle({"a": ["b", "c"], "b": [], "c": []}) is None


def test_two_routes_to_one_name_are_not_a_cycle() -> None:
    """Returns None for a diamond, where a name is reached twice but never left."""
    assert find_cycle({"a": ["b", "c"], "b": ["d"], "c": ["d"]}) is None
    assert find_cycle({"a": ["b", "c"], "b": ["c"], "c": []}) is None


def test_leaves_out_the_names_that_lead_to_the_cycle() -> None:
    """Returns only the names on the cycle, not the path the search took to it."""
    graph = {"start": ["middle"], "middle": ["x"], "x": ["y"], "y": ["x"]}

    found = find_cycle(graph)

    assert is_cycle(graph, found)
    assert sorted(found or []) == ["x", "y"]


def test_lists_the_names_in_dependency_order() -> None:
    """Returns each name followed by one it depends on, not the reverse."""
    graph = {"a": ["b"], "b": ["c"], "c": ["d"], "d": ["a"]}

    found = find_cycle(graph)

    assert found is not None
    start = found.index("a")
    assert found[start:] + found[:start] == ["a", "b", "c", "d"]


def test_a_name_that_depends_on_itself() -> None:
    """Returns a single name for a self-dependency."""
    assert find_cycle({"a": ["a"]}) == ["a"]
    graph = {"a": ["b"], "b": ["b"]}
    assert find_cycle(graph) == ["b"]


def test_finds_a_cycle_in_a_later_part_of_the_graph() -> None:
    """Finds a cycle that cannot be reached from the first names."""
    graph = {"a": ["b"], "b": [], "p": ["q"], "q": ["r"], "r": ["q"]}

    found = find_cycle(graph)

    assert is_cycle(graph, found)
    assert sorted(found or []) == ["q", "r"]


def test_follows_names_that_have_no_entry() -> None:
    """Treats a name that appears only as a dependency as having none of its own."""
    assert find_cycle({"a": ["b"]}) is None
    assert find_cycle({"a": ["b", "a"]}) == ["a"]


def test_agrees_with_a_peeling_check_on_every_small_graph() -> None:
    """Returns a real cycle exactly when one exists, for every small graph.

    Every graph on three names, self-dependencies included, and every graph
    on four names without them.
    """
    names = "abcd"
    for size, allow_self in ((3, True), (4, False)):
        used = names[:size]
        options = []
        for name in used:
            others = [other for other in used if allow_self or other != name]
            options.append(
                [
                    list(c)
                    for n in range(len(others) + 1)
                    for c in combinations(others, n)
                ]
            )
        for chosen in product(*options):
            graph = dict(zip(used, chosen, strict=True))
            found = find_cycle(graph)
            if has_cycle(graph):
                assert is_cycle(graph, found), (graph, found)
            else:
                assert found is None, (graph, found)


def test_leaves_the_graph_alone() -> None:
    """Does not modify the dict or any of its lists."""
    graph = {"a": ["b", "c"], "b": ["a"]}

    find_cycle(graph)

    assert graph == {"a": ["b", "c"], "b": ["a"]}


def test_follows_a_long_chain_without_recursing() -> None:
    """Handles a chain of ten thousand names, with and without a way back.

    The third graph has a cycle of five thousand names at the end of a
    lead-in of five thousand, and only the cycle may be returned.
    """
    size = 10_000
    chain = {f"n{i}": [f"n{i + 1}"] for i in range(size - 1)}
    loop = {**chain, f"n{size - 1}": ["n0"]}
    tailed = {**chain, f"n{size - 1}": ["n5000"]}

    assert find_cycle(chain) is None
    assert is_cycle(loop, find_cycle(loop))
    found = find_cycle(tailed)
    assert is_cycle(tailed, found)
    assert len(found or []) == 5_000
