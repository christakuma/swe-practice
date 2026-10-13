# Merge, then fold

Revealed after grading. LeetCode's nearest relatives are "Merge Intervals"
(56) and "Interval List Intersections" (986).

Inserting one interval into a sorted list had three phases: copy what comes
before, absorb what overlaps, copy what comes after. That shape does not
survive a second *list*. There is no single "before" and "after", and an
interval from either side can absorb intervals from the other.

Trying to keep the three phases — "handle the overlap between `first[i]` and
`second[j]`, then advance one of them" — is where the bugs live. Which one do
you advance? What if the merged result overlaps the *next* interval of the
list you just advanced past?

## The cleaner decomposition

Two independent ideas, each simple:

1. **Merge by start.** Both lists are sorted by start, so repeatedly taking
   the earlier of the two front intervals yields all of them in order of
   start. This is merge sort's merge and nothing else.
2. **Fold into the result.** For intervals arriving in order of start, the
   only interval a new one can overlap is the last one in the result. Extend
   it or append.

```python
if merged and start <= merged[-1][1]:
    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
else:
    merged.append((start, end))
```

Once an interval has been chosen in step 1, which list it came from is
forgotten. Swallowing, chaining, alternating — all the cases that looked
special are the same case.

`max` is not optional: `(2, 3)` arriving after `(1, 10)` overlaps it and must
not pull its end back to 3.

## What the twist was testing

Whether a generalisation is solved by generalising the old code or by
stepping back. Inserting one interval is the special case where one of the
two lists has length one — and the solution to the general problem is
simpler than the special-cased one, not more complicated. `insert` could have
been written as `merge_lists(intervals, [new])` all along.
