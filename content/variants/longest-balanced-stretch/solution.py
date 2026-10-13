"""Reference solution. CI asserts this passes every test in `tests.py`."""

PARTNER = {")": "(", "]": "[", "}": "{"}


def longest_balanced(text: str) -> int:
    """Return the length of the longest balanced stretch of `text`.

    A stack of positions. The bottom entry is the floor: the position of the
    most recent character that can never be matched, or -1 before there is
    one. Above it are the positions of openers still waiting.

    When a closer matches the opener on top, that opener is popped, and
    everything after the new top is balanced -- so the stretch ending here
    has length `position - stack[-1]`. Adjacent stretches join up without
    any extra work, because popping exposes the same entry they were both
    measured from.

    A closer that does not match -- wrong kind, or nothing to match -- is a
    position no balanced stretch can include or reach across, so it becomes
    the new floor. With one kind of bracket a closer can only fail by finding
    nothing to match; with three it can also find the wrong opener, and then
    the openers still waiting below are dead too. Resetting the stack drops
    them. Pushing the closer on top of them would do as well: nothing could
    ever match its way past it.
    """
    stack = [-1]
    longest = 0
    for position, character in enumerate(text):
        if character not in PARTNER:
            stack.append(position)
        elif len(stack) > 1 and text[stack[-1]] == PARTNER[character]:
            stack.pop()
            longest = max(longest, position - stack[-1])
        else:
            stack = [position]
    return longest
