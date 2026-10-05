# Search a Rotated Array — one half is always clean

Revealed after grading. The problem is the classic one (LeetCode 33); the
wording above is ours. It is the natural sequel to
[find the minimum in a rotated array](../find-the-minimum-in-a-rotated-array/notes.md),
and the sibling worth comparing it against — same structure, different binary
search skeleton, for a reason.

## The observation

There is **one** rotation point, so wherever you cut the list, it can fall in
only one half. Which means:

> At every step, at least one half is fully sorted.

That is the whole insight. A sorted half is a half you can reason about with
two comparisons, and reasoning about one half is enough — if the target is not
in it, it is in the other.

## The shape

```python
while low <= high:
    mid = (low + high) // 2
    if numbers[mid] == target:
        return mid

    if numbers[low] <= numbers[mid]:
        keep_left = numbers[low] <= target < numbers[mid]
    else:
        keep_left = not numbers[mid] < target <= numbers[high]

    high = mid - 1 if keep_left else low = mid + 1    # one update, one place
return -1
```

`O(log n)` time, `O(1)` space.

## Decide, then act

The textbook presentation nests four branches, each with its own window update:

```python
if left_is_sorted:
    if target_in_left: high = mid - 1
    else:              low  = mid + 1
else:
    if target_in_right: low  = mid + 1
    else:               high = mid - 1
```

Correct, and `high = mid - 1` appears twice, as does `low = mid + 1`. Those
duplicates are where sign errors hide — you fix one branch, the other still
has the bug, and half your inputs still pass. Naming the decision once
(`keep_left`) collapses it to a single place each window update happens, which
makes the code auditable by reading rather than by tracing.

That is a general habit worth more than this problem: **when the same mutation
appears in several branches, the branching is about a decision, so compute the
decision and mutate once.**

## The `<=` that is not cosmetic

```python
if numbers[low] < numbers[mid]:     # wrong
```

When the window is two elements wide, `(low + high) // 2` rounds down to `low`
— so `numbers[low]` and `numbers[mid]` are **the same element**. A strict
comparison is then false, the code concludes the left half is unsorted, and it
discards the half holding the answer.

The minimal failing input is `[1, 0]` with target `0`: correct answer `1`, the
strict version returns `-1`. That was found by running the buggy variant
against every rotation of every size up to twenty, not by inspection — it
passes every odd-sized hand-picked case, which is most of what anyone writes
by hand.

## Two skeletons, side by side

This kata and the minimum kata are the same structure and want **different
binary searches**, which is the most useful thing to take from doing both:

| | find the minimum | search for a target |
|---|---|---|
| loop | `low < high` | `low <= high` |
| returns | `numbers[low]`, after the loop | from inside, or `-1` |
| window | `high = mid` keeps the candidate | `high = mid - 1` discards it |
| "not found" | impossible | the reason the loop must close |

The minimum search is looking for a **boundary**, which always exists, so it
narrows to one element and reads it. This search is looking for an **exact
value** that may be absent, so the window must be allowed to empty — and that
is why `high = mid` here would hang instead of terminating.

Choosing the wrong skeleton is the dominant failure mode in binary-search
problems, well ahead of arithmetic mistakes. Ask first: *am I finding a
boundary that must exist, or a value that might not?*

## The other acceptable answer

Find the rotation point with the previous kata, then run an ordinary binary
search on whichever run can contain the target. Two passes, `O(log n) +
O(log n) = O(log n)`, and each half is a function you have already written and
tested.

It is genuinely the better answer in production — two simple pieces beat one
clever one — and the prompt allows it. The single-pass version is the one worth
*understanding*, because "at least one half is sorted" is the kind of
structural observation that does not come up unless you look for it.

## With duplicates

Same degradation as the minimum kata. `numbers[low] == numbers[mid]` stops
telling you which half is sorted — `[1, 1, 1, 0, 1]` is opaque at the midpoint
— and the worst case becomes `O(n)`. The standard patch is to advance `low` on
equality. Not a flaw in the patch: with duplicates the problem is genuinely
linear in the worst case.

## What to take away

**A structural guarantee can replace information you do not have.** You never
learn where the rotation point is, and you never need to — knowing that it can
only be in one half is enough to discard the other. Looking for that kind of
guarantee is a more reliable move than trying to recover the missing fact.
