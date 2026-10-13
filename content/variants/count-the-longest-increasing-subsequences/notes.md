# Carry a count beside the length

Revealed after grading. This is "Number of Longest Increasing Subsequence"
(LeetCode 673).

The quadratic solution to the standard problem keeps, for each position, the
length of the longest increasing run ending there. To count, keep how many
runs of that length end there as well. The two columns are updated together:

```python
if numbers[j] < value:
    if lengths[j] + 1 > lengths[i]:      # a strictly better way in
        lengths[i] = lengths[j] + 1
        ways[i] = ways[j]                # replace
    elif lengths[j] + 1 == lengths[i]:   # another way in, just as good
        ways[i] += ways[j]               # add
```

**Replace on better, add on equal.** That one rule is how every "how many
optimal solutions" problem is solved, whatever the optimisation was —
shortest paths, cheapest climbs, fewest coins. A new optimum makes the old
count worthless; a tie pools the counts.

## The two ways to finish wrong

- **Reading one position.** The longest runs can end in several places. In
  `[1, 2, 4, 3]` they end at the 4 and at the 3. Sum over every position
  that reaches the maximum.
- **Counting positions instead of ways.** "How many positions reach the
  maximum" is not the answer either: one position can be the end of many
  runs, as in `[1, 1, 2]`.

## Why the fast solution does not carry over

The standard problem has an `O(n log n)` answer built on a `tails` array and
binary search. That array remembers the best *tail value* for each length and
nothing about how many runs produced it, so there is nothing to add counts
to. Counting in `O(n log n)` is possible, with a Fenwick tree over the values
holding (length, count) pairs — a different and much heavier structure.

A cleverer algorithm usually gets its speed by discarding information, and a
follow-up question is often asking for exactly what was discarded.

## What the twist was testing

Distinguishing *values* from *positions*, which the standard problem lets you
blur. The length does not care that `[1, 3, 3]` has two 3s. The count does.
