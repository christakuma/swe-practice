# Find the Minimum in a Rotated Array — binary search without a target

Revealed after grading. The problem is the classic one (LeetCode 153); the
wording above is ours. It is the best short argument for a particular idea:
**binary search is not about finding a value, it is about halving a search
space using any question you can answer in `O(1)`.**

## What a rotation leaves behind

Rotating a sorted list produces two sorted runs back to back, where every value
in the left run is larger than every value in the right one:

```
[4, 5, 6, 7, 0, 1, 2]
 \_________/  \_____/
   left run    right run
```

There is exactly one place where the list steps *down*, and the minimum is the
first element after it. So the problem is "find the step-down", and that is a
boundary — which is the shape binary search likes.

## The question to ask at the midpoint

A binary search needs one thing: a test at `mid` that tells you which half to
keep. Here that test is **compare the middle with the last element**:

```python
low, high = 0, len(numbers) - 1
while low < high:
    mid = (low + high) // 2
    if numbers[mid] > numbers[high]:
        low = mid + 1        # mid is in the left run; the answer is past it
    else:
        high = mid           # mid is in the right run; it may be the answer
return numbers[low]
```

`O(log n)` time, `O(1)` space.

## Why the last element and not the first

This is the detail worth understanding rather than memorising. Compare with
`numbers[low]` and an **unrotated** list breaks you: in `[1, 2, 3, 4]` the
middle is not greater than the first, which by that rule means "we are in the
right run, look left" — correct by luck. But in `[3, 4, 5, 1, 2]` the middle is
also not greater than... it is, so you look right. The rule limps along and then
fails on a case like `[2, 3, 4, 5, 1]` depending on how you wrote the tie.

`numbers[high]` has no such ambiguity, because of a fact about the structure:
**every element of the left run is greater than the last element, and every
element of the right run is not.** That is a total characterisation of which
run you are in, available in one comparison, with no special case for a
rotation of zero. The right comparand is the one that makes the invariant
unconditional.

## The asymmetric branches

```python
low = mid + 1     # discards mid
high = mid        # keeps mid
```

They look like a typo and they are the correctness argument. `mid` has been
*proven* not to be the minimum in the first branch, so discarding it is safe
and necessary for progress. In the second it might *be* the minimum, so it must
be kept.

Both of the tidier-looking alternatives are bugs:

- `high = mid - 1` steps over the answer. `test_handles_the_minimum_just_past_the_middle`
  is exactly that input.
- `low = mid` makes no progress when the window is two wide — `mid` rounds down
  to `low`, nothing changes, and the loop spins forever.
  `test_handles_two_elements_either_way_round` is the smallest case that hangs.

A hang rather than a wrong answer is worth noting: in a graded run it surfaces
as a wall-clock timeout, which looks like a performance problem and is actually
a termination bug.

## `low < high`, not `low <= high`

The loop narrows until the window is one element wide, and that element is the
answer. There is no "not found" case here — a non-empty list always has a
minimum — so nothing is returned from inside the loop and no sentinel is
needed. That is a different skeleton from textbook binary search, and
recognising which skeleton a problem wants is most of what makes these
variations hard.

Three skeletons, worth keeping distinct:

| goal | loop | returns |
|---|---|---|
| find an exact value | `low <= high` | inside the loop, or a sentinel |
| find a boundary | `low < high` | `low` after the loop |
| find a count / optimum | `low < high` on the *answer* range | `low` after the loop |

## With duplicates, it degrades

The prompt promises distinct values, which is a real simplification. Allow
duplicates and `numbers[mid] == numbers[high]` tells you nothing — `[1, 1, 1, 0, 1]`
and `[1, 0, 1, 1, 1]` are indistinguishable at the midpoint. The usual fix is
`high -= 1` on equality, which is correct and makes the worst case `O(n)`. That
is not a flaw in the fix: with duplicates the problem genuinely requires `O(n)`
in the worst case, and no cleverness recovers the log.

## What to take away

**Binary search generalises to any predicate that is monotone over the search
space.** Here the predicate is "is this element in the right run?" — false for
a prefix, true for a suffix, and the boundary between them is the answer. No
target value is involved at all.

Once you see it that way, the family opens up: searching a rotated array, the
first bad version, the square root of an integer, the smallest capacity that
finishes the job in time. All of them are "find the boundary where a monotone
predicate flips", and the only real work is naming the predicate and getting
the two branch updates right.
