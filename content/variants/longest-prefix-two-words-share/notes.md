# Sorting puts the answer next to itself

Revealed after grading. A relative of "Longest Common Prefix" (LeetCode 14)
that needs one idea the original does not.

A prefix common to *all* the words is found by scanning columns. A prefix
common to *some two* seems to need every pair — until the words are sorted.

In sorted order, the two words with the longest shared prefix are adjacent.
If some word sorted between them, it would have to start with that same
prefix too, and would be an equally good partner. So:

```python
for first, second in pairwise(sorted(words)):
    ...compare only these two...
```

`n - 1` comparisons instead of `n(n - 1) / 2`.

"Sort, then look only at neighbours" is one of the most reusable moves there
is: closest pair of numbers, duplicate detection, merging intervals, and this.
Whenever a question is about the *most similar* pair, ask whether some
ordering makes similar things adjacent.
