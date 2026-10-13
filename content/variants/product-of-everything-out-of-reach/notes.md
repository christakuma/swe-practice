# Prefix and suffix, read somewhere else

Revealed after grading. A generalisation of "Product of Array Except Self"
(LeetCode 238).

The standard solution multiplies "everything before me" by "everything after
me". Skipping a window does not change that idea at all — it changes where the
two halves stop:

```python
before[max(index - k, 0)] * after[min(index + k + 1, size)]
```

Everything left of the window, times everything right of it.

The standard solution is usually written with the prefix folded into the
output array and the suffix into a single running variable, to get `O(1)`
extra space. That trick depends on reading the prefix *at the current index*,
and it does not survive the generalisation: here the two halves are read at
positions the loop has not reached, so both arrays are kept.

That is a fair thing to say out loud in an interview: the clever
space-saving version was specialised to the easy case, and the honest version
with two arrays is the one that generalises.
