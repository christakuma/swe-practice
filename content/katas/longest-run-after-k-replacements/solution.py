"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_run(text: str, k: int) -> int:
    """Return the longest uniform run obtainable with at most `k` changes.

    A window can be made uniform within budget exactly when

        len(window) - (count of its most common character) <= k

    because every character that is not the most common one has to be replaced.
    That condition gets *harder* to satisfy as the window grows, which is what
    licenses a sliding window: grow on the right, and shrink from the left only
    while the condition fails. Each end moves forward at most n times, so the
    scan is linear.

    **`most_common` is never decreased, and that is deliberate.** It is
    therefore sometimes stale -- larger than any count actually in the current
    window. The answer is still correct, and the reason is worth working out
    rather than taking on trust:

    A stale `most_common` only ever makes the condition look *easier*, so the
    window can be left wider than it should be. But `best` is only updated to
    the current width, and a window is only widened when a new character
    arrives -- so for `best` to grow past its true value, some window would
    have to genuinely contain `most_common` of a single character. The stale
    value cannot manufacture a longer answer; it can only delay shrinking, and
    a window that is too wide never reports a width it has not reached.

    Put the other way round: the answer is the maximum over all valid windows,
    and relaxing the validity test cannot raise that maximum unless a genuinely
    valid wider window exists.

    This is the part of the kata worth remembering, and not because the trick
    saves time -- recomputing `max(counts.values())` on each step is O(26) and
    perfectly fine. It is worth remembering because **it is an invariant that is
    deliberately allowed to be wrong, justified by what the result is used
    for.** That is a real technique and an easy one to misapply.
    """
    counts: dict[str, int] = {}
    best = 0
    most_common = 0
    left = 0

    for right, character in enumerate(text):
        counts[character] = counts.get(character, 0) + 1
        most_common = max(most_common, counts[character])

        while (right - left + 1) - most_common > k:
            counts[text[left]] -= 1
            left += 1

        best = max(best, right - left + 1)

    return best
