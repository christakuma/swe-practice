# Count the columns, not the rows

Revealed after grading. A well-known hard follow-up to "Counting Bits"
(LeetCode 338); the same idea underlies "Number of Digit One" (LeetCode 233).

The standard problem fills a table with one entry per number. Asking for the
*total* with `n` near `10**18` makes any per-number work impossible, and the
way out is to turn the picture on its side.

```
n   binary        column 0: 0 1 0 1 0 1 0 1     (cycle of 2)
0   000           column 1: 0 0 1 1 0 0 1 1     (cycle of 4)
1   001           column 2: 0 0 0 0 1 1 1 1     (cycle of 8)
...
```

Each column is periodic. Among the `n + 1` numbers, column `i` contains
`(n + 1) // 2**(i+1)` complete cycles with `2**i` ones each, plus a partial
cycle that contributes `max(remainder - 2**i, 0)`.

About sixty columns for any 64-bit `n`.

"Sum over all numbers of f(number)" can very often be rewritten as "sum over
positions of how many numbers have a contribution there". Swapping the order
of the two sums is the single most useful trick in counting problems of this
kind.
