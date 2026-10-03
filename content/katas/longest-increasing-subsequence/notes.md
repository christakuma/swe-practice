# Two solutions, and the second one stores something different

## The O(n²) one, which is the one to write first

```python
best = [1] * len(numbers)
for i in range(len(numbers)):
    for j in range(i):
        if numbers[j] < numbers[i]:
            best[i] = max(best[i], best[j] + 1)
return max(best, default=0)
```

`best[i]` is the length of the longest increasing subsequence **ending at i**.
Textbook DP: a subproblem per position, a recurrence over all earlier positions,
and the answer is the maximum over the table rather than its last entry.

Perfectly good, and it is the version to reach for when n is a few hundred.

## The O(n log n) one, which inverts the table

Instead of "the longest run ending at this position", store **the smallest value
that can end a run of each length**:

```
tails[k] = the smallest value that ends an increasing subsequence of length k+1
```

That list is sorted — a longer run must end at a larger value — so each new
element is placed by binary search:

- larger than everything in `tails` → it extends the longest run, so append
- otherwise → replace the first entry it is not larger than

```
[10, 9, 2, 5, 3, 7, 101, 18]

10    tails [10]
 9    tails [9]            9 replaces 10
 2    tails [2]
 5    tails [2, 5]
 3    tails [2, 3]         3 replaces 5
 7    tails [2, 3, 7]
101   tails [2, 3, 7, 101]
 18   tails [2, 3, 7, 18]  18 replaces 101
answer 4
```

**Why replacing loses nothing:** a run of length k ending in a smaller value is
at least as useful as one ending in a larger value — anything that could extend
the larger one can extend the smaller one too. So the replacement can never
shorten a future answer, and `len(tails)` is correct at the end.

## `tails` is not an answer

In the trace above the final `tails` is `[2, 3, 7, 18]`, and `2, 3, 7, 18` is
**not** an increasing subsequence of the input — the 18 comes after the 101, and
101 is not in the list. `tails` is a record of best-known endings, not a run.

Its *length* is the answer. Recovering the subsequence itself needs a
predecessor index recorded per element as it is placed, then a walk backwards
from the last appended element. Worth knowing because the length is almost never
what anyone wants, and reading `tails` back as the answer is a bug that passes
every length-based test.

## `bisect_left` is where "strictly" lives

| call | meaning |
|---|---|
| `bisect_left` | strictly increasing — an equal value replaces |
| `bisect_right` | non-decreasing — an equal value appends |

One function name, and `[7, 7, 7, 7]` is 1 or 4 depending on which. That is the
entire difference between the two variants of this problem, which makes it the
kind of detail worth checking against the specification rather than against
intuition.

## Why anyone cares

LIS is the core of `diff`: the longest common subsequence of two files reduces
to an LIS on index positions, which is how `git diff` finds the lines that did
not change. It also shows up in box-stacking, scheduling, and anywhere "pick a
compatible increasing chain" appears — and it is the standard example of a DP
whose complexity improves by changing what the table *means* rather than by
optimising the loops.
