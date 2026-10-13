# Track the range, not the reading

Revealed after grading. This is "Valid Parenthesis String" (LeetCode 678).

With known brackets a single counter is enough: up for an opener, down for a
closer, never below zero, zero at the end. A star makes the counter uncertain,
and the move is to carry the uncertainty instead of resolving it.

```python
fewest, most = 0, 0     # the range of possible open counts
```

- `(` raises both. `)` lowers both.
- `*` lowers `fewest` (it might be a closer) and raises `most` (it might be an
  opener).

Two rules keep the range honest:

- **`most < 0` is fatal.** Even with every star so far read as an opener there
  is a closer with nothing to match.
- **`fewest` is clamped at 0.** Going negative would mean a star was read as a
  closer with nothing open. That reading is not allowed, so it is simply not
  one of the possibilities any more.

At the end the string balances if `fewest == 0`.

## Why counting alone is not enough

"Are there enough stars to cover the difference between openers and closers?"
is the tempting shortcut and it ignores order. `*(` has one star and is one
opener out of balance — and cannot be fixed, because the star comes first. The
range catches that: after `*(` it is `1..2`, and zero is not in it.
