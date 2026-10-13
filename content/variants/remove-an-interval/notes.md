# Two pieces at most, and neither may be empty

Revealed after grading. This is "Remove Interval" (LeetCode 1272).

Inserting had to track a growing merged interval across the list. Removing is
simpler: every interval can be dealt with on its own.

```python
if end <= cut_from or start >= cut_to:
    kept.append((start, end))          # untouched
    continue
if start < cut_from:
    kept.append((start, cut_from))     # the part before
if end > cut_to:
    kept.append((cut_to, end))         # the part after
```

All four comparisons are doing boundary work. The first two use `<=` and `>=`
because half-open intervals that merely touch have nothing in common. The last
two are strict so that an interval starting exactly where the removal starts
does not leave a zero-length `(3, 3)` behind.

That is the lesson of every interval problem, repeated: the algorithm is easy
and the endpoints are where it is wrong.
