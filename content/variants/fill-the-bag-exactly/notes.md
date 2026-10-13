# The loops are identical. The first row is not.

Revealed after grading.

Put the two versions side by side and the difference is one line:

```python
best = [0] * (capacity + 1)                   # at most capacity
best = [0] + [-math.inf] * capacity           # exactly capacity
```

Everything after it — items in the outer loop, weights descending in the
inner one, `best[w] = max(best[w], best[w - weight] + value)` — is the same
code doing the same thing.

## Why the initial row decides it

A table is defined by what its entries *mean*, and the first row is that
meaning applied to "no items yet".

- **At most.** `best[w]` = most value in a bag of capacity `w`. With no
  items, an empty bag is a perfectly good answer for every `w`: all zeros.
- **Exactly.** `best[w]` = most value at total weight exactly `w`. With no
  items, only `w = 0` is achievable. Everything else is *impossible*, which
  is not the same as worth nothing.

Minus infinity is the honest way to write "impossible" in a maximisation.
`-inf + value` is still `-inf`, and `max` never picks it over a real number,
so impossibility flows through the recurrence with no `if`.

## Two smaller traps

- **Do not use -1 inside the table.** `-1 + 10 = 9` looks like a fine value,
  and an impossible state has just become a possible one.
- **Do not test the result with `<= 0`.** For a capacity of zero the correct
  answer *is* zero.

## What the twist was testing

That a dynamic-programming table is a claim, and initialisation is where the
claim is first made. People memorise the knapsack loops and treat the
`[0] * n` as boilerplate. This variant, the counting variant ("how many ways
to fill it", starting from `[1, 0, 0, ...]`) and the feasibility variant
(`[True, False, ...]`) are all the same loops under different first rows.
