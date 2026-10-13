# Same window, different prize

Revealed after grading. A follow-up to "Longest Repeating Character
Replacement" (LeetCode 424).

## What stays the same

Take any stretch of the string. To make it uniform you get rid of everything
that is not its commonest character. That is `width - most` characters,
whether "get rid of" means replace or delete. So **which stretches you can
afford has not changed**, and neither has the window that finds them.

## What changes

What the stretch is worth.

- Replace: the minority characters *become* the run. You get `width`.
- Delete: they vanish. You get `most`.

```python
for right, character in enumerate(text):
    counts[character] = counts.get(character, 0) + 1
    most = max(most, counts[character])
    if right - left + 1 - most > k:
        counts[text[left]] -= 1
        left += 1
return most          # was: len(text) - left
```

One line.

## Not "minus k"

Since `width = most + spent`, it is tempting to take the replacement answer
and subtract `k`. That assumes the window spent all of `k`. `"aaa"` with
`k = 1`: the replacement answer is 3, nothing was spent, and the deletion
answer is 3, not 2. It fails whenever the best run has fewer than `k`
strangers within reach.

## The stale maximum, again

The lazy window never recomputes `most` when it slides, so `most` can
describe a window that is no longer there. For replacement that was fine
because the answer was the width. Here `most` is the answer, so it is fair
to ask whether a stale one can be trusted.

It can, for two reasons:

- **It was real.** `most` only rises when some character's count in the
  current window sets a new record, and the window was affordable at that
  moment.
- **Nothing beats it.** Once the window has had to slide, its width is
  always `most + k`. The best stretch for deletions, widened until it holds
  `k` strangers, is an affordable stretch of width `best + k` or more — and
  the window finishes at least that wide.

Before relying on that argument it was checked against a brute force on
every string of up to nine characters over three letters, for every `k` up
to four. No disagreements; "replacement answer minus k" disagreed 8,352
times.

## The slow version that looks fine

One window per distinct character — "longest stretch with at most k
non-a's, then the same for b…" — is correct and is `O(n)` per character. On
ordinary text that is twenty-six passes. On a string with four thousand
different characters it is four thousand.

## What the twist was testing

Whether you can say what your window *means*. `width = kept + spent` was
always true; the original problem just never asked for the pieces
separately. An interviewer who swaps "replace" for "delete" wants to see you
find the one line that changes, and not take the shortcut that is only
right when the budget is fully used.
