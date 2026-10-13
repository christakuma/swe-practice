# One XOR gives you a clue, not an answer

Revealed after grading. The follow-up to "Missing Number" that every
interviewer has ready; the technique is the one from "Single Number III"
(LeetCode 260).

XOR the range against the list and everything present cancels. With one value
missing, what is left *is* the answer. With two, what is left is `a ^ b`, and
the instinct is that the trick has run out.

It has not. `a ^ b` is non-zero because `a != b`, and each 1 bit in it is a
position where the two differ:

```python
bit = both & -both        # any set bit will do; this is the lowest
```

Split every number — the range's and the list's — by whether it has that bit.
`a` lands in one group and `b` in the other, so each group has exactly **one**
value missing, and XOR-ing a group against itself recovers it. One is enough:
the other is `both ^ first`.

Sums work too (`a + b` from the totals, `a² + b²` from the squares, solve the
pair), and that is a fine answer in an interview. The XOR version is the one
that generalises: "split on a bit where they differ" is how two unknowns are
pulled apart whenever a fold has merged them.
