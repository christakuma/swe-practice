# One character, and the only one that matters

Revealed after grading. The interviewer's version of this is "…and what if the
meetings are back to back?" — the same problem as merge-intervals with the
endpoint convention changed.

```python
if merged and start < merged[-1][1]:      # closed intervals: <=
```

That is the entire difference. Closed intervals `(1, 3)` and `(3, 5)` share
the point 3 and merge. Half-open ones share nothing: the first is over at the
instant the second begins.

## Why it is worth a kata of its own

Because nobody gets interval problems wrong on the algorithm. Sort by start,
sweep, extend or append — that part is the same in every one of them. What
goes wrong is the comparison at the boundary, and it goes wrong *silently*:
a `<=` where a `<` belongs passes every test that does not contain two
intervals that exactly touch.

So before writing the sweep, settle two things out loud:

1. **Are the endpoints included?** Closed `[a, b]`, or half-open `[a, b)`.
   Times and array slices are almost always half-open; ranges of whole things
   — pages, days of the month — are usually closed.
2. **What does touching mean here?** Then write that pair down as a test
   case, next to one that overlaps by a single unit.

## What the twist was testing

Whether the comparison in your merge was a decision or a habit. In an
interview this follow-up takes ten seconds to answer if you know which
character encodes the convention, and a rewrite if you do not.
