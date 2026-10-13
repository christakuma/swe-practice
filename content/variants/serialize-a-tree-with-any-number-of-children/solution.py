"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class Node:
    """A tree node with any number of children, in order."""

    def __init__(self, value: int, children: list[Node] | None = None) -> None:
        self.value = value
        self.children: list[Node] = children if children is not None else []


def serialize(root: Node | None) -> str:
    """Pack a tree into a string.

    Pre-order, each node written as its value and its number of children.
    The count is what fixes the shape: without it a pre-order list of values
    could be any tree at all. An explicit stack rather than recursion,
    because the tree may be ten thousand deep; children are pushed in
    reverse so that they come off in order.
    """
    if root is None:
        return ""
    parts: list[str] = []
    stack = [root]
    while stack:
        node = stack.pop()
        parts.append(f"{node.value} {len(node.children)}")
        stack.extend(reversed(node.children))
    return " ".join(parts)


def deserialize(data: str) -> Node | None:
    """Unpack a string produced by `serialize`.

    `owed` holds the nodes still waiting for children and how many each is
    waiting for. Every node read is attached to the top entry, after
    discarding any entries that are now complete, and then joins the stack
    with its own count.
    """
    if not data:
        return None
    tokens = data.split()
    root = Node(int(tokens[0]))
    owed = [[root, int(tokens[1])]]
    for at in range(2, len(tokens), 2):
        while owed[-1][1] == 0:
            owed.pop()
        parent = owed[-1][0]
        owed[-1][1] -= 1
        node = Node(int(tokens[at]))
        parent.children.append(node)
        owed.append([node, int(tokens[at + 1])])
    return root
