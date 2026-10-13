"""Reference solution. CI asserts this passes every test in `tests.py`."""


def safe_names(dependencies: dict[str, list[str]]) -> list[str]:
    """Return the names from which no chain of dependencies reaches a cycle.

    A name is safe exactly when all of its dependencies are, and a name with
    none is safe outright. So safety spreads upward from the leaves:
    `waiting[name]` counts the dependencies not yet known to be safe, and
    each newly safe name lowers the count of everything that depends on it.

    Anything on a cycle never reaches zero, because it is waiting on itself;
    anything that depends on a cycle waits on that. Iterative, so a chain of
    ten thousand costs no stack.
    """
    waiting: dict[str, int] = {}
    dependents: dict[str, list[str]] = {}
    for name, needed in dependencies.items():
        distinct = set(needed)
        waiting[name] = len(distinct)
        for other in distinct:
            waiting.setdefault(other, 0)
            dependents.setdefault(other, []).append(name)

    ready = [name for name, count in waiting.items() if count == 0]
    safe = []
    while ready:
        name = ready.pop()
        safe.append(name)
        for dependent in dependents.get(name, ()):
            waiting[dependent] -= 1
            if waiting[dependent] == 0:
                ready.append(dependent)
    return sorted(safe)
