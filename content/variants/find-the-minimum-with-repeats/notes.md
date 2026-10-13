# Equal means "no information", not "go left"

Revealed after grading. This is "Find Minimum in Rotated Sorted Array II"
(LeetCode 154).

With distinct values, comparing the middle with the last value always gives a
direction. With repeats there is a third outcome, and the code for the
standard version quietly treats it as one of the other two:

```python
if numbers[mid] > numbers[high]:
    low = mid + 1
else:
    high = mid            # also taken when they are EQUAL
```

`[3, 3, 1, 3]` has a middle equal to its last value. That branch moves `high`
to the middle and discards the 1.

Equality carries no information about where the minimum is. What it does say
is that the last value is redundant — the middle is a copy of it:

```python
else:
    high -= 1
```

One value is discarded instead of half of them, which is why the worst case is
linear. A list of a million equal values with a single smaller one hidden in
it cannot be answered faster; the best any method can do is be logarithmic
whenever the comparisons are informative.
