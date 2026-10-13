"""Your solution goes here. The tests import `build_time` from this module."""


def build_time(
    durations: dict[str, int], dependencies: dict[str, list[str]]
) -> int | None:
    """Return how long it takes for every task to finish.

    Args:
        durations: how long each task takes, by name. Every task is a key.
        dependencies: for some tasks, the names of the tasks that must finish
            before it can start. A task with no entry depends on nothing.

    Returns:
        The time at which the last task finishes, when every task starts as
        soon as its dependencies allow and any number may run at once. None
        if the dependencies form a cycle.
    """
    raise NotImplementedError
