"""Reference solution. CI asserts this passes every test in `tests.py`."""


def smallest_window(text: str, pattern: str) -> str:
    """Return the shortest substring of `text` holding `pattern` in order.

    Forward to find where a match can end, backward to find how late it can
    start.

    The forward walk matches the pattern greedily from `scan`. The position
    where its last character matches is the *earliest* end of any window
    starting at `scan` or later -- taking each pattern character at its
    first opportunity can only finish sooner.

    The backward walk starts at that end and matches the pattern in
    reverse, again greedily, which finds the *latest* start for a window
    with that end. Earliest end, then latest start for it: no window with
    that end is shorter.

    The scan then resumes one past the *start* just found. Resuming past
    the end would be a different algorithm and a wrong one: the next window
    can begin inside this one. In `"axaa"` with pattern `"aa"`, the first
    window is `"axa"`, and the answer `"aa"` starts on its last character.

    Windows are met in order of start, so replacing the best only when a
    new one is strictly shorter keeps the earliest among equals.

    The cost is at most the pattern's length times the text's in ordinary
    cases; the constraints keep that product small.
    """
    if not pattern:
        return ""

    best_start, best_length = 0, len(text) + 1
    scan = 0
    while True:
        matched = 0
        end = scan
        while end < len(text):
            if text[end] == pattern[matched]:
                matched += 1
                if matched == len(pattern):
                    break
            end += 1
        if end == len(text):
            break

        start = end
        matched = len(pattern) - 1
        while True:
            if text[start] == pattern[matched]:
                matched -= 1
                if matched < 0:
                    break
            start -= 1

        if end - start + 1 < best_length:
            best_start, best_length = start, end - start + 1
        scan = start + 1

    return (
        text[best_start : best_start + best_length] if best_length <= len(text) else ""
    )
