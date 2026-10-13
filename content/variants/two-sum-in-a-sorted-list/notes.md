# Sorted input turns a lookup into a walk

Revealed after grading. This is "Two Sum II" (LeetCode 167), which is where the
1-based positions come from.

The standard problem is solved by remembering: a dict answers "have I seen the
complement?" in constant time and costs `O(n)` memory. This version takes the
memory away and hands you an ordering instead, and the ordering is worth
exactly as much.

```python
low, high = 0, len(numbers) - 1
while low < high:
    total = numbers[low] + numbers[high]
    if total == target:
        return (low + 1, high + 1)
    if total < target:
        low += 1
    else:
        high -= 1
```

**Why a step never skips the answer.** Suppose the sum is too small. The low
value has just been paired with the *largest* value still in play and it was
not enough, so no remaining partner can rescue it — it is out, and `low` moves.
Too big is the mirror image and retires the high value. Every comparison
discards one value with a proof attached, which is why one pass is enough.

## What the twist was testing

Two things, and only one of them is about algorithms.

The first is whether you **re-read the constraints** when a problem looks
familiar. The dict solution is correct here. It is also the answer to a
question that was not asked: it never uses the fact that the list is sorted,
and "this input has structure I am not using" is the most reliable smell there
is that a better solution exists.

The second is the **1-based positions**. It is a single `+ 1`, and it is the
part of this exercise that fails in an interview — not because it is hard but
because the familiar version's return value is already in your fingers.
