# From "is it there?" to "how many are there?"

Revealed after grading.

The standard problem promises exactly one answer, and the solution leans on
that promise harder than it looks: it stores *one position per value*,
overwrites freely, and returns at the first hit. Remove the promise and each
of those becomes a bug.

The fix is small and worth being able to derive:

```python
seen = {}
for value in numbers:
    pairs += seen.get(target - value, 0)    # every earlier partner at once
    seen[value] = seen.get(value, 0) + 1    # then record this one
```

The dict holds a **tally**. When a number arrives, every earlier copy of its
complement is a distinct partner, so the whole tally is added.

## Why each pair is counted exactly once

A pair has an earlier position and a later one. It is counted when the loop
reaches the later one — and only then, because at the earlier one its
partner has not been recorded yet. No halving, no `i < j` check.

## The traps

- **Half the target.** With a target of 6, a 3 needs another 3. Looking up
  *before* recording means a 3 finds only the earlier 3s. Record first and
  it finds itself: `[3, 4]` reports a pair.
- **Counting values instead of positions.** A set of values, or a dict that
  is overwritten, sees `[1, 9, 9, 9]` as one pair. There are three.
- **Counting both directions.** Summing `count[value] * count[complement]`
  over every value counts each pair twice, and the half-target case needs
  `n(n-1)/2` rather than `n²`. It can be made to work; the one-pass tally
  never has the problem.

The answer can be large — every pair of a hundred thousand equal values is
about five thousand million — which is a fair hint that no solution can
afford to look at pairs one at a time.

## What the twist was testing

Whether "exactly one pair" was noticed as a constraint doing real work. The
most valuable habit with a familiar problem is to ask which sentence of the
prompt your solution depends on, and what breaks when it goes.
