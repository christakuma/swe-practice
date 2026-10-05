# Maximum Product Subarray — why one running value is not enough

Revealed after grading. The problem is the classic one (LeetCode 152); the
wording above is ours. It exists to be compared with
[maximum subarray](../maximum-subarray/notes.md). They look like the same
problem with a different operator, and the difference between them is a real
property of arithmetic rather than a detail.

## What Kadane's relies on

Kadane's algorithm carries one running value — the best sum ending here — and
discards a running total the moment it goes negative, because a negative prefix
can only hurt whatever follows. That reasoning depends on addition being
**monotone**: adding a larger number always gives a larger result, so a worse
prefix stays worse forever.

## Why multiplication breaks it

Multiplication is not monotone across a negative. A large *negative* running
product is not a dead end — it is one negative value away from being the
largest answer in the list:

```
[-2, 3, -4]
```

The best run is the whole thing, worth `24`. A solution carrying only the best
product ending at each position throws away the `-2` as useless and answers `3`.

So the useful state is a **pair**: the best *and the worst* product ending
here. The worst one is being kept precisely because it is the most promising
thing you have if a negative shows up next.

## The move

Each new value has three candidates, because a run ending here either starts
here or extends the previous one:

```python
best = worst = answer = numbers[0]
for value in numbers[1:]:
    candidates = (value, value * best, value * worst)
    best, worst = max(candidates), min(candidates)
    answer = max(answer, best)
return answer
```

`O(n)` time, `O(1)` space.

Including bare `value` is what lets a run start fresh — and it is also how
**zeros** are handled with no branch at all. After a zero both running values
collapse to `0`, and the next value's bare candidate restarts the run. A
solution that special-cases zeros is solving a problem it does not have.

## Three ways to get it almost right

**Overwriting `best` before computing `worst`.** `best` is read when computing
the new `worst`, so sequential assignment computes the worst from a value that
no longer exists. The tuple assignment above makes it impossible; written as
two statements it is a bug that survives every all-positive test.

**Seeding with `1`.** The identity for multiplication is `1`, which is the
natural-looking seed and is wrong here, because the run must be **non-empty**.
`max_product([-5])` has to return `-5`, and a seed of `1` reports `1` — the
empty product, which is not an allowed answer.
`test_requires_a_non_empty_run` is that case.

**Tracking only `best` and returning it.** `best` is the best run *ending at
the last position*; the question asks for the best run *anywhere*. Same
separation Kadane's needs, same reason `answer` is a third variable.

## On finding the bugs

Two of the expected values in this kata's test suite were wrong when first
written, including one computed by hand for `[2, -5, -2, -4, 3]` — asserted
`120`, actually `24`. The content suite caught it immediately, and then every
literal expectation in the file was re-checked against the brute-force oracle
programmatically rather than by eye.

Worth recording because it is the same lesson as the counter-examples in
[find a word in a grid](../find-a-word-in-a-grid/notes.md): **a number you
worked out in your head is a guess until something executes it.** For a problem
where sign interactions decide the answer, hand-computation is exactly the
wrong tool.

The exhaustive sweep is also deliberately length six rather than seven. Seven
is a further factor of seven in cases and pushed this file to eight seconds
against a ten-second limit — the sort of margin that passes locally and fails
on a loaded CI box.

## What to take away

**Before reusing an algorithm with a different operator, check which of its
properties the reasoning depended on.** Kadane's needs monotonicity; addition
has it and multiplication does not. The fix is not a patch, it is carrying
enough state that the non-monotone case is still represented — and "track the
best *and* the worst" is the general form, useful anywhere an operation can
reverse order.
