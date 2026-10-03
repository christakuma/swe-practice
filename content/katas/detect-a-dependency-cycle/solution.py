"""Reference solution. CI asserts this passes every test in `tests.py`."""


def has_cycle(dependencies: dict[str, list[str]]) -> bool:
    """Whether the dependency graph contains a cycle.

    One visited set is not enough, and that is the whole kata. A node you have
    already finished with is not evidence of a cycle -- a diamond, where two
    paths rejoin at the same node, revisits it legitimately. What makes a cycle
    is arriving at a node that is still **on the current path**.

    So two sets: `finished` for nodes whose whole subtree is explored and can be
    skipped, and `on_path` for the chain of calls above us. A single set collapses
    them and reports every diamond as a cycle; `on_path` alone is correct and
    exponential, because a diamond is then re-explored on every path into it.

    Iterative with an explicit stack, because a chain of ten thousand
    dependencies is ten thousand frames, and Python stops at a thousand. The
    `(node, expanded)` pairs are how a stack imitates the two halves of a
    recursive call: the first visit pushes the children, the second pops the node
    off the path. Recursion gets that for free, which is why the recursive
    version is the one to write first and read later.
    """
    finished: set[str] = set()
    on_path: set[str] = set()

    for start in dependencies:
        if start in finished:
            continue
        stack: list[tuple[str, bool]] = [(start, False)]
        while stack:
            node, expanded = stack.pop()
            if expanded:
                on_path.discard(node)
                finished.add(node)
                continue
            if node in finished:
                continue
            if node in on_path:
                return True
            on_path.add(node)
            stack.append((node, True))
            for neighbour in dependencies.get(node, ()):
                if neighbour not in finished:
                    stack.append((neighbour, False))
    return False
