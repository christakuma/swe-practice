# Rewrite the question as a difference and it becomes a lookup

Let `P[i]` be the sum of the first `i` elements, with `P[0] = 0`. Then the sum
of the slice from `start` to `end` is

```
sum(numbers[start:end]) == P[end] - P[start]
```

So the slice sums to `target` exactly when `P[start] == P[end] - target`. Fix
`end` and the question stops being "which slices work" and becomes **"how many
earlier prefixes had this particular value"** — which a dict answers in O(1).

```
numbers:  1   1   1        target 2
P:      0   1   2   3
                           at P=2: seen P=0 once  -> 1 slice
                           at P=3: seen P=1 once  -> 1 slice
                           total 2
```

Counts rather than positions, because the question is how many — and the same
prefix sum can occur many times, which is precisely what happens when the list
contains zeros or cancelling negatives.

## `{0: 1}` is the base case, not an off-by-one

The empty prefix has sum zero and it has occurred once before you look at
anything. Without that seed, a slice that starts at index 0 has no earlier
prefix to pair with, and `count_subarrays([3], 3)` returns 0. It is the single
most common bug in this problem and the suite tests it on its own.

## Why a sliding window does not apply

The window technique needs the sum to **increase** as the window widens, so
that an over-large sum can be fixed by moving the left edge in. With negatives
that fails: `[1, -1, 0]` widening from `[1]` to `[1, -1]` makes the sum smaller.
There is no monotone quantity, so there is no invariant to maintain, and no
amount of care rescues it.

That is worth separating clearly, because the two techniques look adjacent:

| values | "sum equals k" | "sum at most k" |
|---|---|---|
| all non-negative | window or prefix sums | sliding window |
| any sign | **prefix sums + dict** | no easy answer |

## The family this belongs to

"Count pairs of positions whose aggregate differs by X" is one pattern wearing
many hats:

- slices summing to `k` → prefix sums, this kata
- slices summing to a **multiple** of `k` → key on `running % k`
- the **longest** such slice → store the *first* index per prefix sum instead
  of a count, and take the widest gap
- slices with equal numbers of two kinds of element → key on the running
  difference, target 0

The shape is always: a running aggregate, a dict keyed on it, and a restatement
of the question as "what earlier value am I looking for". Recognising it is
worth more than any one of the variants.

## Complexity

O(n) time, one pass. O(n) space — the dict can hold a distinct prefix sum per
element, and `[1, 2, 4, 8, ...]` is an input where it does.
