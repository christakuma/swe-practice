# Not "seen before" but "seen lately"

Revealed after grading. This is "Contains Duplicate II" (LeetCode 219).

The standard problem needs a set: has this value turned up? Adding a distance
turns the question into *where* did it last turn up, so the set becomes a dict
from value to position.

```python
if value in last_seen and position - last_seen[value] <= k:
    return True
last_seen[value] = position
```

**Overwrite every time.** For the value at the current position, the nearest
earlier copy is the most recent one. Keeping the *first* position instead is
the characteristic bug: `[1, 0, 1, 1]` with `k = 1` then measures both later
1s from position 0 and misses the neighbours at the end.

The other way to see it is a window: a set holding only the last `k` values,
dropping the one that falls out as you advance. Same cost, and memory bounded
by `k` rather than by the number of distinct values.
