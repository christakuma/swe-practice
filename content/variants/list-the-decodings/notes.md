# Counting forgets; listing has to remember

Revealed after grading. The "print them all" follow-up to "Decode Ways"
(LeetCode 91).

Counting needed two integers. Each step asked "how many ways to here?" and
could throw away everything else. Listing cannot throw anything away: the
answer *is* the paths, so the walk has to carry the string built so far.

```python
for width in (1, 2):
    piece = digits[at : at + width]
    if len(piece) == width and int(piece) <= 26:
        letters.append(chr(64 + int(piece)))
        extend(at + width)
        letters.pop()
```

Append, recurse, pop: the backtracking shape. The rules have not changed — a
leading zero ends the branch, a pair above 26 is not a letter.

**The cost changed class.** The count is linear in the length. The list is
as long as the count itself, which grows like the Fibonacci numbers — twenty
1s have 10,946 decodings. That is why the constraint on the length dropped
from ten thousand digits to twenty.

"Now return them all" is a standard escalation, and the honest first answer
is about cost: the output can be exponentially large, so no algorithm can be
fast, and the table that made counting cheap no longer helps.
