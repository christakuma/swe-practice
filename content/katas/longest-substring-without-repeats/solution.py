"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_unique_run(text: str) -> int:
    """Return the length of the longest run of characters with no repeats.

    A sliding window, where the only interesting question is what to do when the
    window is no longer valid. The naive answer -- walk `start` forward one
    character at a time until the duplicate is gone -- is correct and makes the
    whole thing quadratic in the worst case.

    Remembering the *index* of each character instead of just whether it has been
    seen is what collapses that: a duplicate at `index` means the window cannot
    start any earlier than one past the previous occurrence, so `start` jumps
    there directly and every character is visited once.

    `max(start, ...)` is the part that is easy to leave out and hard to notice.
    Without it a stale entry -- a character last seen *before* the current window
    began -- drags `start` backwards, and the window silently stops being valid.
    `"abba"` is the shortest input that proves it.
    """
    last_seen: dict[str, int] = {}
    start = 0
    longest = 0
    for index, character in enumerate(text):
        if character in last_seen:
            start = max(start, last_seen[character] + 1)
        last_seen[character] = index
        longest = max(longest, index - start + 1)
    return longest
