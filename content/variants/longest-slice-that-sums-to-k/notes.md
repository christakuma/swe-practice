# Same dict, different thing stored in it

Revealed after grading. This is "Maximum Size Subarray Sum Equals k"
(LeetCode 325).

Both versions rest on one identity: the slice from `start` to `end` sums to
`prefix[end] - prefix[start]`. So "a slice ending here sums to the target"
means "`prefix - target` was a prefix sum earlier".

- **How many** such slices? → store how many times each prefix sum has
  occurred.
- **How long** is the longest? → store **where each prefix sum first
  occurred**.

```python
start = first_seen.get(prefix - target)
if start is not None:
    longest = max(longest, position - start)
first_seen.setdefault(prefix, position)     # first sighting only
```

`setdefault` is the entire difference. Assigning `first_seen[prefix] =
position` every time keeps the *latest* sighting and returns the shortest
slice ending at each position instead of the longest.

## The empty prefix

`first_seen = {0: 0}` says the sum of nothing is 0, at position 0. Leave it
out and any slice that starts at index 0 goes missing — `[1, 2, 3]` with a
target of 6 answers 0.

## Why not a sliding window

With non-negative values, a window works: grow on the right, shrink on the
left when the sum is too big, and it is `O(1)` space. That relies on the sum
only ever rising as the window grows. One negative value breaks it — the
window shrinks away from a slice that would have come back to the target.
The prefix-sum dict makes no assumption about signs.

## What the twist was testing

That the dict's *values* were understood as a design choice. Counting, first
position, last position, the minimum prefix so far — each answers a
different question about slices with the same loop. Deciding what to
remember is most of solving a prefix-sum problem.
