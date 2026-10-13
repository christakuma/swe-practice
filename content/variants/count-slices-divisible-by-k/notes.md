# Same remainder, not same difference

Revealed after grading. This is "Subarray Sums Divisible by K" (LeetCode 974).

The standard problem looked up `total - k` among the earlier running totals.
This one looks up the earlier totals with the same *remainder*:

```python
remainder = total % k
count += seen.get(remainder, 0)
seen[remainder] = seen.get(remainder, 0) + 1
```

Two totals with the same remainder differ by a multiple of `k`, and that
difference is a slice's sum. The dict now has at most `k` keys however long
the list is.

**The signature did not change, and that is the trap.** `(numbers, k)` reads
exactly like the standard problem, and a solution to that one returns a
plausible number here. Read what the second argument *means* before reusing
code that takes one.

**Negative remainders.** Python's `%` gives `-1 % 5 == 4`, so negative totals
land in the right bucket by themselves. C, Java and JavaScript give `-1`, and
there this needs `((total % k) + k) % k`. Worth saying in an interview even
when writing Python.
