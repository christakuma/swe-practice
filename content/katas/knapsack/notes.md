# The direction of the inner loop *is* the 0/1 constraint

```python
for weight, value in items:
    for remaining in reversed(range(weight, capacity + 1)):
        best[remaining] = max(best[remaining], best[remaining - weight] + value)
```

Reverse the inner loop and you have solved a different problem.

- **Downwards**: when `best[remaining]` is computed, `best[remaining - weight]`
  has not yet been touched *for this item* — it still describes the previous
  items only. So the item is used at most once. This is 0/1 knapsack.
- **Upwards**: `best[remaining - weight]` has already been updated for this
  item, so taking it again is allowed. This is **unbounded** knapsack, where
  each item is available in unlimited quantity.

One `reversed`, two problems, and nothing else in the code distinguishes them.
The suite tests it directly: one item of weight 2 and value 3 with capacity 6
must give 3, and the upward loop gives 9.

That is the single most useful thing to remember about knapsack-shaped DP. When
a one-dimensional table is a collapsed two-dimensional one, the iteration
direction encodes which row you are allowed to read.

## Why greedy loses

Three plausible greedy rules, each with a short counter-example:

| rule | counter-example | greedy | best |
|---|---|---|---|
| most valuable first | `[(3, 30), (2, 20), (2, 20)]`, cap 4 | 30 | 40 |
| best value per weight | `[(10, 60), (20, 100), (30, 120)]`, cap 50 | 160 | 220 |
| lightest first | `[(1, 1), (5, 100)]`, cap 5 | 1 | 100 |

The ratio rule is the dangerous one because it is **nearly** right — it is
exactly optimal for the *fractional* knapsack, where items can be cut. The
moment items are indivisible, the last item you pick may leave capacity you
cannot use, and the ratio rule has no way to look ahead to that.

Which is a good instinct to carry: greedy optimality often depends on a
continuity assumption, and "you cannot take half a thing" is exactly the
assumption that breaks it.

## "O(items × capacity)" is not polynomial

It looks polynomial and it is not, because `capacity` is a *number* in the
input, not a count of things. A capacity of a billion takes a billion cells,
while the input describing it is ten characters. That is **pseudo-polynomial**:
polynomial in the numeric value, exponential in the number of bits.

0/1 knapsack is NP-hard, and this table is not a counter-example to that — it is
why the distinction exists. Practically it means the table is the right answer
when capacities are small and the wrong answer when they are large, in which
case you are reaching for branch-and-bound or an approximation.

## Recovering which items

The one-dimensional table says what the best value is and not how. For the
items, keep the full `items × capacity` table and walk back from the corner: at
each step, if `table[i][c] != table[i-1][c]`, item `i` was taken, so move to
`table[i-1][c - weight]`.

O(items × capacity) space instead of O(capacity) — and, as with
[edit distance](../edit-distance/notes.md), the collapsed table buys space by
throwing away the path, which is usually the thing the caller wanted.

## The family

| problem | change |
|---|---|
| unbounded knapsack | inner loop upwards |
| subset sum | values equal weights; ask whether `best[capacity] == capacity` |
| partition into two equal halves | subset sum for half the total |
| [coin change](../coin-change/notes.md) | unbounded, minimising count instead of maximising value |
| bounded (k copies each) | expand each item into k, or a per-item inner loop |

All one table and one recurrence, which is the reason knapsack is worth knowing
by shape rather than by heart.
