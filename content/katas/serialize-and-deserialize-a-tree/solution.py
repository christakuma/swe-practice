"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

NOTHING = "#"
SEPARATOR = ","


class TreeNode:
    """A binary tree node."""

    def __init__(
        self,
        value: int,
        left: TreeNode | None = None,
        right: TreeNode | None = None,
    ) -> None:
        self.value = value
        self.left = left
        self.right = right


def serialize(root: TreeNode | None) -> str:
    """Pack a binary tree into a string.

    Pre-order, with an explicit marker for every absent child. The markers are
    the entire design: a traversal of only the nodes that exist loses the
    shape, because many different trees produce the same list of values. The
    absences are data.

    That is the same realisation as in `are-two-trees-the-same`, where a
    comparison had to reject "exactly one is None" to mean "same shape" -- and
    the same as in `encode-and-decode-strings`, where a format that cannot
    represent its own edge cases cannot be decoded. Here the edge case is a
    missing child, and writing it down is what makes the string faithful.

    Pre-order specifically, because it puts a node **before** its children:
    the reader can create a node and then recursively fill its left and right
    from whatever follows. In-order cannot be deserialised at all without extra
    information -- the root is somewhere in the middle and nothing says where.
    """
    parts: list[str] = []

    def visit(node: TreeNode | None) -> None:
        if node is None:
            parts.append(NOTHING)
            return
        parts.append(str(node.value))
        visit(node.left)
        visit(node.right)

    visit(root)
    return SEPARATOR.join(parts)


def deserialize(data: str) -> TreeNode | None:
    """Unpack a string produced by `serialize`.

    The mirror of the writer, and it works because pre-order hands the reader
    exactly what it needs next: a token that is either a value -- make a node,
    then read its left subtree, then its right -- or the marker, meaning
    nothing here.

    **The reader must consume tokens in sequence across recursive calls.** An
    iterator does that; re-scanning or re-splitting inside each call does not,
    and is the usual way this comes out quadratic or simply wrong. Each `next`
    advances a position shared by the whole recursion, which is what makes
    "whatever comes next" well defined.

    The separator is safe here in a way it is not in
    `encode-and-decode-strings`, and for a reason worth stating rather than
    assuming: the payloads are **integers**, whose decimal representation
    cannot contain a comma. A separator is only sound when the alphabet of the
    payload excludes it -- which is a property of this problem, not a general
    licence.
    """
    tokens = iter(data.split(SEPARATOR))

    def build() -> TreeNode | None:
        token = next(tokens)
        if token == NOTHING:
            return None
        node = TreeNode(int(token))
        node.left = build()
        node.right = build()
        return node

    return build()
