"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_run(text: str, k: int) -> int:
    """Return the longest uniform run obtainable with at most `k` deletions.

    This is the replacement version's window, unchanged, with a different
    thing returned at the end.

    A stretch of the string can be made uniform by deleting its minority
    characters, and that costs `width - most`, where `most` is the count of
    its commonest character -- the same price replacing them had. So the
    affordable stretches are the same ones. What they are worth is not:
    replacing yields the whole width, deleting yields only `most`.

    The window here is the lazy one. It never shrinks, and `most` is the
    highest count any character has reached in any window so far, which can
    be stale for the window currently held. For the replacement problem that
    was harmless because the answer was the width. Here `most` *is* the
    answer, so it needs its own argument, in two halves:

    - It is achievable. `most` only rises when a character's count in the
      current window reaches a new high, and the window is affordable at
      that moment: it grew by one and its commonest count grew by one.
    - It is not beaten. The window's width is always `most + k` once it has
      had to slide. Take the best stretch for deletions and widen it until
      it holds `k` minority characters; that is an affordable stretch of
      width `best + k` or more, the window ends at least that wide, and so
      `most` is at least `best`. If the text runs out before `k` minority
      characters are found, the window never slides at all and `most` is the
      commonest character's count in the whole text.

    The answer is *not* the replacement answer minus `k`. That holds only
    when the best window really does contain `k` characters to spend on.
    """
    counts: dict[str, int] = {}
    left = most = 0
    for right, character in enumerate(text):
        counts[character] = counts.get(character, 0) + 1
        most = max(most, counts[character])
        if right - left + 1 - most > k:
            counts[text[left]] -= 1
            left += 1
    return most
