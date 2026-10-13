"""Reference solution. CI asserts this passes every test in `tests.py`."""


def find_cycle(dependencies: dict[str, list[str]]) -> list[str] | None:
    """Return the names of one dependency cycle, in order.

    A depth-first search that keeps the current path as a list, with
    `position` recording where on it each name sits. A dependency that is
    already on the path closes a cycle, and the cycle is the path **from that
    name onwards** -- everything before it is only how the search got there.

    `done` holds names whose dependencies have all been explored without
    finding a cycle. Meeting one again is a second route to the same place
    and nothing more, so it is skipped, which is also what keeps the search
    linear.

    The recursion is unrolled into a stack of iterators, one per name on the
    path. A chain of ten thousand names is ten thousand frames otherwise.
    """
    done: set[str] = set()
    for start in dependencies:
        if start in done:
            continue
        path = [start]
        position = {start: 0}
        pending = [iter(dependencies.get(start, ()))]
        while pending:
            for following in pending[-1]:
                if following in position:
                    return path[position[following] :]
                if following not in done:
                    position[following] = len(path)
                    path.append(following)
                    pending.append(iter(dependencies.get(following, ())))
                    break
            else:
                pending.pop()
                finished = path.pop()
                del position[finished]
                done.add(finished)
    return None
