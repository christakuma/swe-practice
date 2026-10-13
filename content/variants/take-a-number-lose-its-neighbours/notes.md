# The houses were hiding in the values

Revealed after grading. This is "Delete and Earn" (LeetCode 740).

Nothing in the statement mentions a row, and the positions in the list mean
nothing. The row appears once the list is reduced to its distinct values in
sorted order — there, the things that exclude each other are next to each
other, and it is the houses again.

```python
if previous is not None and value == previous + 1:
    taken, skipped = skipped + worth[value], best_before
else:
    taken, skipped = best_before + worth[value], best_before
```

**The gap case is the one change.** In a real row every neighbour excludes
you. Here `1` and `3` are neighbours in the sorted order and do not conflict,
so taking `3` builds on the best so far, whatever it was.

**Do not index an array by value.** The common solution allocates
`max(numbers) + 1` buckets. With a value of a billion that is the whole
machine. Sorting the distinct values costs `O(n log n)` and no more memory
than the input.
