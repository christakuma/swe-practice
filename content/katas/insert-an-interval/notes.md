# Insert an Interval — three groups, one pass

Revealed after grading. The problem is the classic one (LeetCode 57); the
wording above is ours. It is a short problem whose whole content is **not
throwing away a guarantee you were given**.

## The guarantee

The input is already sorted and already disjoint. That means the intervals fall
into three **consecutive** groups:

1. entirely before the new one,
2. touching it,
3. entirely after.

Contiguous, in that order, always. So one pass handles each in turn:

```python
while index < count and intervals[index][1] < start:
    result.append(intervals[index]); index += 1          # group 1

while index < count and intervals[index][0] <= end:
    start = min(start, intervals[index][0])
    end = max(end, intervals[index][1]); index += 1      # group 2
result.append((start, end))

result.extend(intervals[index:])                          # group 3
```

`O(n)`, no sorting.

## Why not just sort and merge

```python
return merge(sorted([*intervals, new]))
```

Correct, `O(n log n)`, and it reuses
[merge intervals](../merge-intervals/notes.md) verbatim. It is also the wrong
answer here, because it **discards the fact that the input was sorted** and
pays to rediscover it.

Worth contrasting the two problems deliberately: `merge-intervals` *has* to
sort, because its input is unordered and sorting is what makes overlaps
adjacent. This one must not. Same domain, same merging logic, and the
preconditions differ — which is the thing to read first in any interval
problem.

(The sort-and-merge version is the oracle in the test suite, for exactly that
reason: it shares none of the three-group reasoning.)

## Widen, then emit once

The absorbing loop does not append anything. It widens `start` and `end`, and
the merged interval is emitted after the run ends.

Emitting as you go cannot work, because a later interval may extend the *same*
block. `test_merges_several_overlaps` is the case: `(4, 8)` reaches across
three intervals, and a solution that emits on first overlap returns several
pieces where there should be one.

## The comparison that appears twice

**Touching counts as overlapping**: `(1, 3)` and `(3, 5)` merge into `(1, 5)`.

So "entirely before" is `end < start` and not `end <= start`. And "still
overlapping" is `interval.start <= end`, not `<`.

That is one character in each of two places, and they have to agree. A solution
that gets one right and the other wrong **merges on the left and not on the
right** — which looks like a weird asymmetric bug and is really one
inconsistency. `test_merges_intervals_that_merely_touch` checks both
directions, and `insert([(1, 3), (5, 7)], (3, 5))` checks them at once: the new
interval touches its neighbours on both sides and everything becomes `(1, 7)`.

**Whether the endpoints are inclusive is a modelling decision and it belongs in
the prompt.** Half-open intervals `[start, end)` would make touching *not*
overlap, and most real interval code uses them for exactly that reason — it
removes this class of off-by-one entirely. This kata uses closed intervals
because the classic statement does, and it is worth knowing which convention
you are in before writing a single comparison.

## One index, three loops

The three stages share `index` rather than slicing the list into parts. One
place the position advances, so the groups cannot overlap or skip — a slicing
version has to get three boundaries right instead of one.

## A test that contained its own bug

The long-list test originally asserted a hand-counted length,
`25_000 + 1 + 25_000`, which is 50,001. The answer is 50,000: counting how many
unit intervals fall strictly before 250,000 is precisely the off-by-one the
test exists to catch, and I put it in the expectation instead.

It now compares against the oracle. **When the expected value requires the same
arithmetic as the code under test, do not compute it by hand** — delegate it to
something with different failure modes.

## What to take away

**Read the preconditions before choosing the algorithm.** "Sorted" and
"disjoint" are not decoration; here they collapse an `O(n log n)` problem to
`O(n)` and remove the need to merge at all except in one contiguous run.
Re-sorting sorted input is the most common way to leave a free constant factor
on the table — and the second most common is not noticing that the problem
*didn't* promise sortedness.
