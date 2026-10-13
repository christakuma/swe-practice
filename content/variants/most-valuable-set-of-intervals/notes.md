# Greedy stops working the moment the intervals stop being equal

Revealed after grading. This is weighted interval scheduling; LeetCode has it
as "Maximum Profit in Job Scheduling" (1235).

The standard problem has a beautiful greedy answer: sort by end, keep
everything that fits. It works because of an exchange argument — the interval
that ends first can always be swapped into an optimal solution without making
it worse — and that argument quietly assumes any interval is as good as any
other.

Give them values and the swap can lose. `(0, 2)` worth 1 ends before `(0, 3)`
worth 9. No ordering rescues it: highest value first loses to several small
ones that add up; best value per unit of length loses too.

## What survives is the sort

Sorting by end still buys something, just not a decision. For any interval,
the ones compatible with it and earlier in the order are a **prefix**: the
ones ending at or before its start. So:

```python
best[i] = max(best[i - 1],              # leave interval i out
              value + best[prefix(i)])  # take it, plus the best of what fits before
```

and `prefix(i)` is a binary search over the sorted ends. `bisect_right`,
because an interval ending exactly at `start` is compatible.

That is `O(n log n)` — the sort and one search per interval. The plain
version scans backwards for the prefix and is `O(n^2)`.

## What the twist was testing

Whether you know *why* your greedy algorithm was correct. A greedy rule is a
proof wearing a disguise, and the proof has assumptions. When an interviewer
adds weights, costs or values to a problem you solved greedily, they are
removing one of them, and the usual landing place is dynamic programming over
the same sorted order.
