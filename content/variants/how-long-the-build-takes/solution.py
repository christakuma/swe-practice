"""Reference solution. CI asserts this passes every test in `tests.py`."""


def build_time(
    durations: dict[str, int], dependencies: dict[str, list[str]]
) -> int | None:
    """Return how long it takes for every task to finish.

    Kahn's algorithm carrying one number per task. `ready_at[task]` is the
    latest finish among the dependencies processed so far -- the earliest
    moment the task could start. A task comes off the queue only when all
    its dependencies have been processed, so by then `ready_at` is final and
    the task's finish time is that plus its duration.

    Each finished task pushes its finish time forward into its dependants,
    keeping the maximum, and releases any whose last dependency it was.

    The answer is the largest finish time seen: the length of the longest
    chain of dependencies, measured in time. If fewer tasks were processed
    than exist, the rest are waiting on each other.
    """
    dependants: dict[str, list[str]] = {name: [] for name in durations}
    waiting = dict.fromkeys(durations, 0)
    for name, needs in dependencies.items():
        for needed in needs:
            dependants[needed].append(name)
            waiting[name] += 1

    ready_at = dict.fromkeys(durations, 0)
    queue = [name for name, count in waiting.items() if count == 0]
    longest = 0
    for name in queue:
        finish = ready_at[name] + durations[name]
        longest = max(longest, finish)
        for dependant in dependants[name]:
            ready_at[dependant] = max(ready_at[dependant], finish)
            waiting[dependant] -= 1
            if waiting[dependant] == 0:
                queue.append(dependant)
    return longest if len(queue) == len(durations) else None
