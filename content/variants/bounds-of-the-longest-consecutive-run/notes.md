# The answer was already in your hands

Revealed after grading. A "return it, don't just measure it" follow-up to
"Longest Consecutive Sequence" (LeetCode 128).

The linear algorithm finds each run's start — a value whose predecessor is
absent — and walks up to its end. It always knew both. The standard problem
only asked for the difference.

```python
if best is None or (start - end, start) < (best[0] - best[1], best[0]):
    best = (start, end)
```

**The tie rule belongs in the comparison.** Iterating a set visits runs in no
particular order, so "the first one found" is not a rule at all — it gives
different answers on different runs. Ranking by `(-length, start)` makes the
result independent of the order of the loop.

Whenever a problem says "return any" and a follow-up says "return the
smallest", check whether your code was relying on iteration order. With sets
and dicts of integers it often looks deterministic and is not something to
depend on.
