# The same pointers, with nothing to hit

Revealed after grading. This is "3Sum Closest" (LeetCode 16).

Sort, fix one value, close two pointers in on the rest: the frame is exactly
three-sum's. What is different is that there may be no exact answer, so the
pointers are not looking for a hit — they are being steered towards the
target while every sum they pass is compared with the best so far.

```python
if (abs(total - target), total) < (abs(best - target), best):
    best = total
```

Ranking by the pair `(distance, sum)` is the tie rule written as a
comparison: closer wins, and at equal distance the smaller sum does.

**What goes away.** Three-sum spent half its code skipping duplicates, because
it returned every distinct triple. This returns one number, so duplicates
cost a little time and nothing else. Carrying the skipping logic across is
harmless; believing it is needed is a sign the old solution was being
adapted line by line rather than re-derived.
