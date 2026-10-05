# Find the Missing Number — a summary that forgets duplicates

Revealed after grading. The problem is the classic one (LeetCode 268); the
wording above is ours. It is a small problem with an unusually good lesson:
the answer comes from choosing a *summary of a collection* with the right
algebraic property, rather than from searching the collection at all.

## The answers that are too expensive

All three of these are correct:

```python
sorted(numbers)                       # O(n log n), then walk for the gap
set(range(n + 1)) - set(numbers)      # O(n) time, O(n) space
seen = [False] * (n + 1)              # O(n) time, O(n) space
```

They work by *recording what they saw*. The problem does not need that — there
is only one missing value, so you only need one number's worth of state.

## The arithmetic summary

You know what the complete range should sum to, in closed form:

```python
return n * (n + 1) // 2 - sum(numbers)
```

`O(n)` time, `O(1)` space, one pass. Gauss's formula is doing the work: the
difference between what should be there and what is there *is* the answer.

## The XOR summary

XOR has three properties that together make it the better summary:

- `x ^ x == 0` — it is its own inverse,
- `x ^ 0 == x` — zero is the identity,
- it is commutative and associative — order does not matter.

So folding XOR over a pile of numbers produces a value that has **forgotten
everything appearing an even number of times**. Arrange for every number in
`0..n` to appear twice except the missing one, and the survivor falls out:

```python
result = 0
for index, value in enumerate(numbers, start=1):
    result ^= index ^ value
return result
```

`start=1` is the detail. The indices then run `1..n`, and `result` is seeded
with `0`, so between the seed and the indices the fold sees every number in
`0..n` exactly once on the index side — and every present value exactly once on
the value side. Everything cancels but the gap.

## Why XOR rather than the sum

In Python, nothing. Integers are arbitrary-precision, so the two are genuinely
interchangeable and the sum is more readable.

In a fixed-width language they are not interchangeable at all. The sum of
`0..n` overflows a signed 32-bit integer at around `n = 92682`, and that is a
real wrong-answer bug on an input the problem permits. The XOR fold **cannot
overflow**, because it never produces a value wider than its widest input. That
is the actual reason this trick is worth owning — not elegance, but that one of
the two summaries has a failure mode and the other does not.

This generalises past the missing number. The same fold finds the one
non-duplicated element in a list where everything else appears twice, and
`a ^ b` lets you swap two values without a temporary. All of it rests on
self-inverseness.

## The test worth reading

`test_finds_every_missing_value_at_every_small_size` checks all 861 (size,
missing) pairs up to n = 40 and makes the hand-picked cases nearly redundant.
Off-by-one errors in this problem are the norm rather than the exception —
`start=1` versus `start=0`, `n` versus `n + 1`, whether the range is inclusive
— and every one of them survives a few spot checks.

The `test_finds_zero` case deserves suspicion for the opposite reason: `0` is
the identity for both XOR and addition, so a thoroughly broken fold often
returns it by accident and *passes*. A test whose expected value is the same as
the failure mode's default value is a weak test. It is kept because the case
genuinely matters, not because it discriminates.

## What to take away

**When you need one fact about a collection, look for a summary with the
algebra you need rather than a record of what you saw.** Sum recovers a missing
addend; XOR recovers an unpaired element; a product recovers a missing factor;
a running minimum recovers the best-so-far. Each is `O(1)` space because it
throws away everything except the one property that matters — which is the same
instinct behind Kadane's algorithm in
[maximum subarray](../maximum-subarray/notes.md).
