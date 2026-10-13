# The tolerance goes in the comparison

Revealed after grading. Sessionisation — "Merge Intervals" (LeetCode 56) with
a tolerance.

```python
for start, end in sorted(intervals):
    if merged and start - merged[-1][1] <= gap:      # was: start <= merged[-1][1]
        merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    else:
        merged.append((start, end))
```

One comparison changed. Everything worth saying is about why it is that one
and not something that looks equivalent.

## Padding is not equivalent

The tempting route is to reuse the function you have:

```python
padded = [(start, end + gap) for start, end in intervals]
return merge(padded)
```

The merging is right and the output is wrong: every result is `gap` too
long. You have to subtract it again, and remember to.

Pad *both* ends — `(start - gap, end + gap)` — and the merging is wrong too.
Two intervals now reach towards each other, and meet when they are `2 * gap`
apart.

Changing the comparison leaves the data alone, so there is nothing to undo.

## Chains

`(1, 2)`, `(4, 5)`, `(7, 8)` with a gap of 2 is one interval, though the
first and last are five apart. That needs no code: each interval is compared
with the **merged interval so far**, whose end moved out when the middle one
joined.

That is also why "sessions" work the way they do. A session has no maximum
length; it lasts until the events stop for longer than the timeout.

## Furthest end, not last end

```
1 ─────────────────── 10
   2 ─ 3                    12 ─ 13
```

Sorted by start, `(2, 3)` comes just before `(12, 13)`. Measured from 3 they
are nine apart. Measured from 10 — where the merged interval actually ends —
they are two. The `max` in the merge line is what keeps the end at 10.

## What the twist was testing

Two things. First, finding the single place in a known algorithm where the
definition of "together" lives, and changing only that. Second, resisting a
transformation of the input that seems to reduce the new problem to the old
one. Reductions like that are worth looking for — and worth checking on the
output as well as the grouping, because they often get one right and not
the other.
