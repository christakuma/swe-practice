# One more state

Revealed after grading. This is "Maximum Subarray Sum with One Deletion"
(LeetCode 1186).

Kadane's algorithm carries one number along the list: the best sum of a slice
that ends *here*. The question at each step is "extend, or start again?".

Allowing a drop adds one bit of history that matters — **has the drop been
used yet?** — so carry one number for each answer:

```python
dropped = max(dropped + value, whole)   # extend an earlier drop, or drop this one
whole   = max(whole + value, value)     # ordinary Kadane
best    = max(best, whole, dropped)
```

"Drop this one" is worth `whole` as it stood at the *previous* element: the
best undropped slice ending just before here, with the current value left
out. That is why `dropped` is updated first.

## Why not fix up the plain answer?

*Find the best slice, remove its most negative element.* The best plain slice
of `[10, -30, -30, 6, -20, 7]` is `[10]`. It has nothing to drop. The answer, 13,
comes from `6, -20, 7` — a slice the plain algorithm never considers, because
without the drop it sums to −7.

The drop changes which slices are worth having, not just what they total. It
has to be inside the recurrence.

## Small print

- `dropped` starts at minus infinity. With one element seen, "a non-empty
  slice with one element dropped" does not exist. Starting it at 0 happens to
  give the same answers -- the first thing done to it is to add a value, which
  makes it an ordinary one-element slice -- but it says something untrue, and
  the place a zero really does damage is `best`: start *that* at 0 and an
  all-negative list answers 0 by keeping nothing.
- The answer is the best over both states. `dropped` alone would force a
  drop, and `[2, 3, 4]` would lose its 2.

## What the twist was testing

The move from one running value to two. The same step turns "best time to
buy and sell" into the at-most-twice version, and "house robber" into its
variants: when a rule adds a yes-or-no fact about the past, the state doubles
and each copy gets its own line.
