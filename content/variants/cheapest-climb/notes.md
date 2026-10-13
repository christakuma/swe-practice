# The same staircase, asked a different question

Revealed after grading. This is "Min Cost Climbing Stairs" (LeetCode 746).

Counting climbs gave `ways(n) = ways(n - 1) + ways(n - 2)`. The structure
behind that — a step is reached from one of the two below it — has not
changed. What is being asked about each route has: not *how many*, but *the
cheapest*. So the plus becomes a `min`, and the step's own cost is added:

```python
before, last = 0, 0
for cost in costs:
    before, last = last, cost + min(before, last)
return min(before, last)
```

That swap is worth remembering as a pattern. Counting paths, cheapest path,
"is there a path" — one recurrence, with `+`, `min` and `or` in the same
place.

## Where it goes wrong

Never in the loop. Always at the ends.

- **The start.** The floor is below step 0, so a two-step move lands on step
  1 without touching step 0. Both starting values are 0. Starting the climb
  *on* step 0 makes `[50, 1, 1]` cost 51.
- **The finish.** The goal is the landing beyond the last step, reachable from
  either of the last two. Returning the cost of standing on the last step
  makes `[1, 2, 50]` cost 51.
- **One step.** Both of the above at once: the answer is 0.

## What the twist was testing

Greed, mostly. "Step on whichever of the next two is cheaper" is right on the
examples that come to mind and wrong on `[1, 2, 100, 1, 100]`, where the
cheaper next step leads you to a place from which every move is expensive.
The standard problem cannot teach that, because counting has no greedy
version to be tempted by.
