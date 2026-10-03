# One decision per element

```python
best_here = max(value, best_here + value)
best_anywhere = max(best_anywhere, best_here)
```

`best_here` is the largest sum of a slice **ending at this element**. There are
exactly two candidates for it: the slice that ends here and extends the previous
one, or the slice that is just this element. Nothing else ends here.

And the choice is easy: extend when the previous `best_here` is positive, start
fresh when it is negative. A prefix with a negative sum can never improve
anything that follows it, so dropping it is always at least as good.

`best_anywhere` is separate because the best slice overall does not have to end
at the last element. Collapsing the two into one variable is the most common bug
in Kadane's, and it shows up only on inputs where the best slice is followed by
something negative.

```
[-2, 1, -3, 4, -1, 2, 1, -5, 4]

value      -2   1  -3   4  -1   2   1  -5   4
best_here  -2   1  -2   4   3   5   6   1   5
best_ever  -2   1   1   4   4   5   6   6   6
```

## The empty-slice question is the whole specification

Seeding with 0 instead of `numbers[0]` encodes "the empty slice, with sum 0, is
allowed". Then `[-3, -1, -2]` returns 0 — which is not the sum of *any* slice of
that list.

Both readings are defensible problems. The difference is one line, and the
difference in the answer appears only on all-negative inputs, which is why the
suite tests one explicitly. If you ever use this in anger, say which you mean in
the signature: "largest sum, or 0 if every slice is negative" is a different
function from "largest sum of a non-empty slice".

## Why it is dynamic programming

It does not look like DP because there is no table. But the structure is exactly
the same as [climbing stairs](../climbing-stairs/notes.md):

- a subproblem indexed by position: *best slice ending at i*
- a recurrence relating it to the previous one: `best(i) = max(a[i],
  best(i-1) + a[i])`
- an answer that is an aggregate over all subproblems, not the last one

The table is one cell wide because the recurrence reads back exactly one place —
so it collapses to a variable, the same way Fibonacci's table collapses to two.
"Space-optimised DP" is this observation, and spotting that the window is small
is usually worth more than the table.

## The variants, which are the same loop

| question | change |
|---|---|
| the slice itself, not just its sum | track the start index when you restart |
| largest **product** | track the max *and* the min — a negative times a negative |
| at most k slices | a table, genuinely; the window is no longer small |
| circular list | run it twice: best normal slice, and total minus the worst slice |

The product one is worth thinking about for a minute: the trick that makes the
sum version work — "drop a negative prefix" — is false for products, and the fix
is to carry both extremes because multiplying by a negative swaps them.
