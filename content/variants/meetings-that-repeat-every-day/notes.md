# A clock has no first meeting

Revealed after grading. "Meeting Rooms" (LeetCode 252) on a circle; the
wording above is ours.

The standard version sorted the meetings and compared neighbours, and the
comparison was `next_start >= previous_end`. Both halves of that break here,
and for different reasons.

## An end is not a place any more

`(1320, 120)` ends at 120, and 120 is smaller than every evening start it
ought to be compared with. Nothing is wrong with the meeting. The pair of
numbers has stopped being two points on a line.

What survives is the **length**:

```python
length = (end - start) % DAY
```

That is 60 for `(540, 600)` and 240 for `(1320, 120)`, by the same sum. Once
every meeting is a start and a length, the question "is it over by the next
start?" is `start + length <= next_start`, and midnight has gone from the
comparison.

Splitting a meeting at midnight into two ordinary ones also works, and is
the first thing most people reach for. It doubles the special cases instead
of removing them: a piece that ends at 1440, a piece that starts at 0, and a
meeting ending at midnight exactly that must not leave an empty piece behind.

## The pair the list does not have

Sorted by start, the neighbour argument still holds: a meeting that reaches
past the next start is running when the next one begins, and if none does,
each sits wholly between its own start and the next.

But a list has two ends and a clock does not. The last meeting in start
order is followed by the first one, tomorrow:

```python
following = [start for start, _ in ordered[1:]] + [ordered[0][0] + DAY]
```

`n` meetings, `n` pairs — not `n - 1`. Leaving that pair out passes every
test in which nothing runs through midnight, which is every test the
standard version had.

Writing tomorrow's first start as `+ DAY` rather than reducing a difference
with `% DAY` matters for two cases that are otherwise easy to get backwards.
A single meeting is followed by itself a whole day later, and should pass.
Two meetings with the same start are zero apart, and should fail. Taken
modulo a day, both distances are zero.

## What carries over

A circular problem is usually a linear one plus exactly one extra case, and
the work is finding which. Here it was one more pair. For houses in a circle
it was one more subproblem; for a circular slice it was one more sum. Look
for the single seam before reaching for anything cleverer.
