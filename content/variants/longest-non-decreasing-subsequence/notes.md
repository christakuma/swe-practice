# bisect_left becomes bisect_right

Revealed after grading. The "what if equal values are allowed?" follow-up to
"Longest Increasing Subsequence" (LeetCode 300).

The whole change is one function name:

```python
position = bisect_right(tails, value)     # strict version: bisect_left
```

`tails[k]` is the smallest possible last value of a subsequence of length
`k + 1`. A new value replaces the first tail it cannot follow.

- **Strict:** it cannot follow a tail *equal* to it, so it replaces the first
  tail `>=` itself — `bisect_left`.
- **Non-decreasing:** it can follow an equal tail, so it replaces the first
  tail `>` itself — `bisect_right`.

In the quadratic table the same change is `<` becoming `<=`.

It is a small edit and a real test of understanding, because the patience
algorithm is usually memorised as a recipe. Knowing *which* tail a value
displaces, and why, is what lets you answer this in one line instead of
starting again.
