# Sort by where things end

Revealed after grading. This is "Minimum Number of Arrows to Burst Balloons"
(LeetCode 452).

It is the same greedy as removing the fewest intervals, looked at from the
other side. There, you kept as many non-overlapping intervals as possible;
here, each point you place corresponds to one of those kept intervals, and
everything it touches is an interval that overlapped it.

```python
for start, end in sorted(intervals, key=lambda interval: interval[1]):
    if last is None or start > last:
        points += 1
        last = end
```

**The convention flipped.** In the standard version touching intervals did not
overlap, so the comparison was `>=`. These are closed, a boundary point is in
both, and the comparison is `>`. Carrying the old one across counts
`(1, 2), (2, 3)` as needing two points.

**Sort by end, not start.** The interval that ends first constrains the
choice most, and its end is the best place to stand. Sorting by start lets a
long, early interval decide — `(1, 10), (2, 3), (4, 5)` then gets one point
at 10, which is in neither of the short ones.
