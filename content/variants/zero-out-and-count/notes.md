# Count what you did, not what you intended

Revealed after grading. "Set Matrix Zeroes" (LeetCode 73) with a return value
that has to be earned.

Returning a count looks like a footnote and is where the bugs are. The
tempting formula is arithmetic on the plan — rows to clear times the width,
plus columns to clear times the height. It is wrong twice: a cell in both a
cleared row and a cleared column is counted twice, and cells that were zero
all along are counted as changed.

```python
if value != 0 and (y in rows or x in columns):
    line[x] = 0
    changed += 1
```

Visit each cell once and count it at the moment it is actually changed. No
overlap correction is needed because nothing is visited twice.

Reporting what happened is nearly always safer measured at the point of the
change than derived afterwards from what was supposed to happen.
