"""Reference solution. CI asserts this passes every test in `tests.py`."""

import heapq


def topological_order(dependencies: dict[str, list[str]]) -> list[str] | None:
    """Order the names so that every name comes after everything it depends on.

    Kahn's algorithm: repeatedly take something with nothing left outstanding.
    The counter is `outstanding[name]` -- how many of a name's dependencies have
    not yet been emitted -- and emitting a name decrements the counter of
    everything that depends on it.

    Cycle detection is free and is the part worth noticing: if the loop ends with
    names left over, every one of them is waiting on something that is also
    waiting, which is a cycle. No separate pass, no colours, no path to track.

    The dependents index is built because the dict runs the wrong way. It maps
    each name to the things it depends ON, and the algorithm needs to go the other
    way when something is emitted. Building the reverse index is two lines and
    skipping it means rescanning the whole graph per emitted name.

    A heap rather than a plain list for the ready set, which is a decision about
    the *specification* and not about speed: "any valid order" would let a list
    do, and then two correct solutions disagree and the test suite cannot assert
    on the answer. Picking the alphabetically smallest available name at each step
    makes the output a function of the input.
    """
    names = set(dependencies)
    for needed in dependencies.values():
        names.update(needed)

    outstanding = dict.fromkeys(names, 0)
    dependents: dict[str, list[str]] = {name: [] for name in names}
    for name, needed in dependencies.items():
        for dependency in needed:
            outstanding[name] += 1
            dependents[dependency].append(name)

    ready = [name for name in names if outstanding[name] == 0]
    heapq.heapify(ready)

    order: list[str] = []
    while ready:
        name = heapq.heappop(ready)
        order.append(name)
        for dependent in dependents[name]:
            outstanding[dependent] -= 1
            if outstanding[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(names):
        return None
    return order
