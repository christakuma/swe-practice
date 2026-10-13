"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_run(text: str, k: int, target: str) -> int:
    """Return the longest run of `target` obtainable with at most `k` changes.

    A window is affordable when it holds at most `k` characters that are not
    the target. One counter tracks that, and both edges only ever move
    forward, so the scan is linear and needs no table of character counts.
    """
    best = 0
    start = 0
    others = 0
    for end, character in enumerate(text):
        if character != target:
            others += 1
        while others > k:
            if text[start] != target:
                others -= 1
            start += 1
        best = max(best, end - start + 1)
    return best
