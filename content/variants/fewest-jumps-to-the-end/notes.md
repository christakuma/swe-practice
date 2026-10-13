# A breadth-first search that never builds a queue

Revealed after grading. This is "Jump Game II" (LeetCode 45), with the
unreachable case added back in.

The yes-or-no version needs one number: the furthest position reachable so
far. Asking *how many jumps* needs one idea more, and it is easy to reach for
the wrong one.

**The wrong one is "jump as far as you can".** From `[2, 3, 1, 1, 4]` the
longest first jump lands on a 1 and the trip takes three jumps; stepping one
place to the 3 takes two. A jump should be judged on what it makes reachable
*next*, not on where it lands.

## Layers

Positions reachable in exactly one jump form a contiguous range. So do those
reachable in exactly two, and so on — each layer starts where the last one
ended. The answer is the layer the final position falls in, which is a
breadth-first search. The ranges are contiguous, so no queue is needed:

```python
for position in range(last):
    furthest = max(furthest, position + jumps[position])
    if position == edge:          # finished scanning this layer
        if furthest == edge:
            return -1             # nothing in it leads anywhere new
        taken += 1
        edge = furthest
```

`edge` is the end of the current layer and `furthest` the end of the next.
Arriving at `edge` is the moment a jump is spent.

## What the twist was testing

Two things. Whether you notice that greedy-by-distance is not the same as
greedy-by-reach — the standard problem never forces the distinction, because
for a yes-or-no answer either works. And whether you put the `-1` back: the
well-known version of this problem promises the end is reachable, so the
well-known solution has no exit for a layer that goes nowhere, and loops or
returns a count for a trip that cannot be made.
