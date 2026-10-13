# Monotone, so it slides

Revealed after grading. This is "Subarray Product Less Than K" (LeetCode 713).

The maximum-product problem had to track a largest and a smallest running
product, because a negative value could turn one into the other. This version
makes every value positive, and that single constraint changes what kind of
problem it is: a longer slice now always has a product at least as large.

That monotonicity is what a sliding window needs.

```python
product *= value
while product >= limit:
    product //= numbers[start]
    start += 1
count += end - start + 1
```

**The count is the window's width.** If `numbers[start..end]` is under the
limit, so is every slice that ends at `end` and starts later. That is
`end - start + 1` slices in one addition, rather than one at a time.

**`limit <= 1` first.** No product is below 1, and without the early return
the `while` loop divides past the end of an empty window.

When a problem says "all positive", ask what that buys. Usually it is exactly
this: something becomes monotone, and a window or a binary search becomes
possible.
