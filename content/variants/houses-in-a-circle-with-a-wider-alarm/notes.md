# Two cases became three

Revealed after grading. A widened "House Robber II" (LeetCode 213).

The standard circle splits into two rows — without the first house, or
without the last — because the only pair the circle adds is those two. Widen
the alarm and the join gets more complicated, and the two-case reduction
quietly stops being enough.

Look at the four houses round the join: second-to-last, last, first, second.
Any two of them are within two places of each other, *except* the outer pair,
which are three apart. So a valid selection leaves out:

- the first two, or
- the last two, or
- the last and the first.

```python
max(_row(houses[2:]), _row(houses[:-2]), _row(houses[1:-1]))
```

The third row is the one a hasty generalisation drops, and `[0, 9, 0, 0, 9,
0]` is the input that needs it.

Whenever a constraint is strengthened, redo the case analysis instead of
editing the old one. The cases came from the constraint.
