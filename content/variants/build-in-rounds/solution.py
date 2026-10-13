"""Reference solution. CI asserts this passes every test in `tests.py`."""


def build_rounds(dependencies: dict[str, list[str]]) -> list[list[str]] | None:
    """Group the names into rounds that depend only on earlier rounds.

    The peeling of a topological sort, a layer at a time. `waiting[name]`
    counts dependencies not yet placed; the names at zero form a round, and
    placing the round lowers the counts of everything that depends on them,
    which yields the next round.

    A name lands in the earliest possible round because it is placed the
    moment its last dependency is. If names remain when a round comes up
    empty, they are waiting on each other, and there is no answer.
    """
    waiting: dict[str, int] = {}
    dependents: dict[str, list[str]] = {}
    for name, needed in dependencies.items():
        distinct = set(needed)
        waiting[name] = len(distinct)
        for other in distinct:
            waiting.setdefault(other, 0)
            dependents.setdefault(other, []).append(name)

    rounds: list[list[str]] = []
    current = sorted(name for name, count in waiting.items() if count == 0)
    placed = 0
    while current:
        rounds.append(current)
        placed += len(current)
        following = []
        for name in current:
            for dependent in dependents.get(name, ()):
                waiting[dependent] -= 1
                if waiting[dependent] == 0:
                    following.append(dependent)
        current = sorted(following)
    return rounds if placed == len(waiting) else None
