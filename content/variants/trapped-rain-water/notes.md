# The lower side is the one you can trust

Revealed after grading. This is "Trapping Rain Water" (LeetCode 42), the
problem every container question is eventually followed by.

In the container problem two lines held water and everything between them was
air. Here every bar is solid, so the answer is a sum over positions:

```
water above bar i = min(tallest to the left, tallest to the right) - height[i]
```

Two arrays of running maxima give that directly in `O(n)` space. The
two-pointer version gets it in `O(1)`:

```python
if tallest_left <= tallest_right:
    tallest_left = max(tallest_left, heights[left])
    water += tallest_left - heights[left]
    left += 1
```

**Why the lower side can be settled.** If the tallest bar seen from the left
is no taller than the tallest seen from the right, then the level above the
left pointer is exactly `tallest_left`: there is certainly something at least
that tall further right. The unknown part of the list cannot lower it.

It is the same argument as the container's — move the pointer that cannot do
better — applied to a different quantity. Recognising that the *argument*
carried over while the formula did not is the point of doing both.
