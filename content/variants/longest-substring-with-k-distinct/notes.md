# The same window, counting something else

Revealed after grading. This is "Longest Substring with At Most K Distinct
Characters" (LeetCode 340).

The standard problem keeps a window in which no character repeats. This one
keeps a window in which no more than `k` different characters appear. The
frame is identical — grow on the right, shrink on the left while the window
is invalid, measure after every step — and the invariant has been swapped
out.

```python
counts[character] = counts.get(character, 0) + 1
while len(counts) > k:
    leaving = text[start]
    counts[leaving] -= 1
    if counts[leaving] == 0:
        del counts[leaving]
    start += 1
best = max(best, end - start + 1)
```

## Why counts and not a set

The no-repeats version could get away with a set, or a dict of last-seen
positions, because a character was either in the window or not. Here a
character can be in the window *several times*, and it only stops being one
of the distinct characters when the last copy leaves. A set cannot know that.
A count can.

**Delete the key at zero.** `len(counts)` is the number of distinct
characters only if nothing sits in the dict with a count of 0. Forget the
`del` and the window thinks it is fuller than it is, shrinks too far, and
under-reports — on exactly the inputs where a character leaves and never
comes back.

## What the twist was testing

Whether you see the sliding window as a pattern with a replaceable condition
or as the solution to one problem. Almost every "longest substring such
that…" question is this loop with a different test in the `while` and a
different thing in the dict. At most k distinct, at most k replacements,
containing every required character — one skeleton, three invariants.

`k = 0` is the edge to check by hand: the `while` empties the window on every
step, and the answer is 0 without a special case.
