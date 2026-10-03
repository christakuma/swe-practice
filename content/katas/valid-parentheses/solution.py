"""Reference solution. CI asserts this passes every test in `tests.py`."""

PAIRS = {")": "(", "]": "[", "}": "{"}


def is_balanced(text: str) -> bool:
    """Whether every bracket in `text` is closed by its matching partner.

    Counting brackets is the answer that almost works and is worth ruling out
    deliberately: `"([)]"` has one of each, balanced counts, and is not valid.
    Nesting is an ordering constraint, and counts have no order.

    What an ordering constraint needs is a stack. Each opener is a promise to
    close; each closer must redeem the most recent outstanding promise. "Most
    recent" is exactly what a stack gives.

    Two failure modes, and both matter: a closer that does not match the top
    (wrong order), and a non-empty stack at the end (promises never kept). A
    solution that forgets the second returns True for `"(("`.
    """
    stack: list[str] = []
    for character in text:
        if character in PAIRS:
            if not stack or stack.pop() != PAIRS[character]:
                return False
        else:
            stack.append(character)
    return not stack
