# The recurrence was never about "one or two"

Revealed after grading. The interviewer's version of this is "what if you
could take up to k steps?"; the general form is LeetCode 377, "Combination
Sum IV", in disguise.

The standard staircase is usually remembered as *it's Fibonacci*, and that
memory is what this variant is designed to trip over. Fibonacci is a
coincidence of the step sizes. The actual idea is:

> the last move was one of the allowed sizes, and before it you were standing
> somewhere you could already count.

```python
ways = [1] + [0] * steps
for height in range(1, steps + 1):
    ways[height] = sum(ways[height - size] for size in sizes if size <= height)
```

With sizes `[1, 2]` that sum has two terms and you get Fibonacci. With
`[1, 2, 3]` it has three. With `[2]` half the table is zero. Nothing else
changes.

## What had to give

**The two rolling variables.** The standard solution keeps only the last two
counts, because that is as far back as it looks. Here the look-back is the
largest step size, so the table has to be kept (or at least a window that
long). An optimisation that was correct for the special case is wrong for the
general one, which is worth noticing before deleting the table out of habit.

**Unreachable heights.** With a 1 in the sizes every height is reachable.
Without one, some are not, and the count is simply `0` — the sum over no
terms. Code that special-cases the bottom of the table for one and two steps
gets this wrong.

## Order matters, and the loops say so

Height is the outer loop and size the inner one, so every size is tried as the
*last move* at every height: `1+5` and `5+1` are both counted. Swap the loops
— all the 1s first, then all the 5s — and you count each multiset once
instead, which is the coin-change question. Same table, same additions,
different loop order, different problem.
