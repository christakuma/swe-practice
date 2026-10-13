"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import build_time

type Graph = dict[str, list[str]]


def by_settling(durations: dict[str, int], dependencies: Graph) -> int | None:
    """Repeatedly finish every task whose dependencies are all finished."""
    finish: dict[str, int] = {}
    while len(finish) < len(durations):
        settled = {
            name: durations[name]
            + max((finish[needed] for needed in dependencies.get(name, [])), default=0)
            for name in durations
            if name not in finish
            and all(needed in finish for needed in dependencies.get(name, []))
        }
        if not settled:
            return None
        finish.update(settled)
    return max(finish.values(), default=0)


def test_a_dependency_must_finish_first() -> None:
    """Adds a task's duration to its dependency's when one waits for the other."""
    assert build_time({"compile": 5, "test": 3}, {"test": ["compile"]}) == 8


def test_independent_tasks_run_side_by_side() -> None:
    """Takes as long as the slowest task when nothing depends on anything."""
    assert build_time({"a": 3, "b": 7, "c": 5}, {}) == 7
    assert build_time({"only": 4}, {}) == 4


def test_a_task_waits_for_its_slowest_dependency() -> None:
    """Starts a task when the last of its dependencies finishes, not the first."""
    assert build_time({"a": 3, "b": 4, "c": 5, "d": 1}, {"d": ["a", "b", "c"]}) == 6
    assert build_time({"a": 9, "b": 1, "c": 2}, {"c": ["b", "a"]}) == 11


def test_the_longest_chain_decides() -> None:
    """Follows the chain that takes longest, not the one with most tasks.

    One chain has three quick tasks and the other a single slow one.
    """
    durations = {"a": 1, "b": 1, "c": 1, "slow": 10, "end": 2}
    dependencies = {"b": ["a"], "c": ["b"], "end": ["c", "slow"]}

    assert build_time(durations, dependencies) == 12


def test_it_is_not_the_sum_and_not_the_number_of_stages() -> None:
    """Is neither the total of all durations nor one slowest task per stage.

    The slow task in the first stage feeds nothing; the quick one feeds the
    slow task of the second stage.
    """
    durations = {"quick": 1, "slow": 10, "after": 8}
    dependencies = {"after": ["quick"]}

    assert build_time(durations, dependencies) == 10
    assert build_time({"x": 2, "y": 5, "z": 4, "w": 1}, {"z": ["x"], "w": ["y"]}) == 6


def test_a_shared_dependency_is_built_once() -> None:
    """Counts a task that several others depend on a single time."""
    durations = {"base": 4, "left": 2, "right": 3, "top": 1}
    dependencies = {"left": ["base"], "right": ["base"], "top": ["left", "right"]}

    assert build_time(durations, dependencies) == 8


def test_returns_none_for_a_cycle() -> None:
    """Returns None when tasks wait on each other, however far away the cycle is."""
    assert build_time({"a": 1, "b": 1}, {"a": ["b"], "b": ["a"]}) is None
    assert build_time({"a": 1}, {"a": ["a"]}) is None
    assert (
        build_time(
            {"ok": 5, "x": 1, "y": 1, "z": 1}, {"x": ["y"], "y": ["z"], "z": ["x"]}
        )
        is None
    )


def test_no_tasks_take_no_time() -> None:
    """Returns 0 when there is nothing to build."""
    assert build_time({}, {}) == 0


def test_tolerates_empty_and_repeated_dependency_lists() -> None:
    """Handles a task listed with no dependencies, and one listed twice."""
    assert build_time({"a": 2, "b": 3}, {"a": [], "b": ["a", "a"]}) == 5


def test_agrees_with_settling_task_by_task() -> None:
    """Matches a round-by-round simulation for every small build.

    Every dependency graph on three tasks, self-dependencies included, with
    every assignment of the durations 1, 2 and 5.
    """
    names = "abc"
    options = [
        [list(c) for n in range(4) for c in combinations(names, n)] for _ in names
    ]
    for chosen in product(*options):
        dependencies = dict(zip(names, chosen, strict=True))
        for times in product((1, 2, 5), repeat=3):
            durations = dict(zip(names, times, strict=True))
            expected = by_settling(durations, dependencies)
            assert build_time(durations, dependencies) == expected, (
                durations,
                dependencies,
            )


def test_leaves_its_arguments_alone() -> None:
    """Does not modify either dict."""
    durations = {"a": 1, "b": 2}
    dependencies = {"b": ["a"]}

    build_time(durations, dependencies)

    assert durations == {"a": 1, "b": 2}
    assert dependencies == {"b": ["a"]}


def test_handles_a_long_chain_and_a_wide_build() -> None:
    """Handles ten thousand tasks in a chain, and ten thousand side by side.

    In a chain nothing can overlap, so the time is the sum. Side by side,
    it is the slowest task. Closing the chain into a ring leaves no task
    able to start.
    """
    size = 10_000
    durations = {f"t{i}": i % 7 + 1 for i in range(size)}
    chain = {f"t{i}": [f"t{i - 1}"] for i in range(1, size)}

    assert build_time(durations, chain) == sum(durations.values())
    assert build_time(durations, {}) == 7
    assert build_time(durations, {**chain, "t0": [f"t{size - 1}"]}) is None
