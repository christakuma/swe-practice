# Reset to zero

Revealed after grading. The classic companion to "Longest Common Subsequence"
(LeetCode 1143; the substring form is LeetCode 718 on arrays).

Both problems fill a table over the two strings, and the two recurrences
differ in one branch:

```
                 characters match          characters differ
subsequence      diagonal + 1              max(up, left)
substring        diagonal + 1              0
```

A subsequence may skip, so a mismatch inherits the best so far. A substring
may not, so a mismatch ends the run and the count starts again.

Two consequences follow from that one change. The cell no longer means "best
overall" — it means "length of the run ending exactly here" — so **the answer
is the maximum over the whole table**, not the bottom-right corner. And the
table for the substring problem is mostly zeros.

Choosing what a cell *means* is the real decision in any table problem. "Best
so far" and "best ending here" are the two standard choices, and a constraint
of contiguity nearly always calls for the second.
