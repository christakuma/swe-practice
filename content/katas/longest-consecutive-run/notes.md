# Longest Consecutive Run — recognise the start

Revealed after grading. The problem is the classic one (LeetCode 128); the
wording above is ours. It is the best example in the library of a **nested loop
that is linear**, and of why being able to argue the bound matters more than
recognising the shape of the code.

## The set, and then the actual idea

A set makes "is `x + 1` present?" constant-time, so a run can be walked upward
from any of its members. It also collapses duplicates for free, which is why
`[5, 5, 5]` is a run of one with no special case.

That alone is not enough. Walking up from *every* value is quadratic: on a
single run of `n` values, each member walks the rest of it.

The idea:

> **A run has exactly one value that can start it — the one whose predecessor
> is absent.**

```python
present = set(numbers)
best = 0
for value in present:
    if value - 1 in present:
        continue                    # not a start; counted from below
    length = 1
    while value + length in present:
        length += 1
    best = max(best, length)
return best
```

## Why the nested loop is O(n)

Worth being able to say out loud, because the code looks quadratic:

- The outer loop runs once per distinct value: `O(n)`.
- The inner loop runs **only for run-starts**, and across all run-starts its
  total work is the sum of the run lengths — which is at most the number of
  distinct values.

So the two loops together do `O(n)` work. Each value is visited once by the
outer loop and at most once by some inner walk.

**The guard is not an optimisation to add later — without it the complexity
claim is simply false.** And the time limit notices: measured, the unguarded
version scales cleanly quadratically (0.08s at n=2000, 0.35s at 4000, 1.39s at
8000), which extrapolates to about **870 seconds** at the 200,000-value run
`test_handles_one_long_run_without_quadratic_work` uses. Against a 15-second
limit.

That is the useful thing about this kata: the two solutions differ by one
`continue`, they are both "use a set", and one of them does not finish.

## Walking up, not down

Symmetric versions exist — check `value + 1` is absent and walk downward — and
they are equally correct. But a solution that walks downward from every value
*without* a guard blows up on **descending** input rather than ascending, which
is why `test_handles_a_long_run_given_in_reverse` exists. A single large test
in one direction can bless the wrong half of the symmetry.

## Sorting is the other good answer

```python
values = sorted(set(numbers))
best = run = 1
for previous, current in pairwise(values):
    run = run + 1 if current == previous + 1 else 1
    best = max(best, run)
```

`O(n log n)` time, `O(1)` extra space if you may mutate the input. It is
shorter, clearer, and the one to reach for unless someone has specified linear.

It is banned here because it rests on a genuinely different idea — *arranging*
for runs to be adjacent, rather than *recognising* where a run begins. It is
also the oracle in the test suite, for exactly that reason: two solutions that
can only agree by both being right.

## What to take away

**A nested loop's bound depends on how often the inner loop runs, not on its
being nested.** Amortised arguments like this one — total inner work bounded by
the size of the input, not by the outer loop count — come up constantly:
sliding windows where both ends only move forward, the two-pointer walks in
[three sum](../three-sum-to-zero/notes.md), path compression in
[count connected components](../count-connected-components/notes.md).

The habit worth building: when you write a nested loop and believe it is
linear, **state the reason**. If the reason is "the inner loop usually doesn't
run much", you have a guess. Here the reason is a partition — every value
belongs to exactly one run, and each run is walked once — and that is a proof.
