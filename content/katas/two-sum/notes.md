# Two Sum — why the dict is the answer

Revealed after grading. The problem is the classic one (LeetCode 1); the
wording above is ours, and the point of it here is the trade, not the trick.

## The obvious solution, and what is wrong with it

```python
for i in range(len(numbers)):
    for j in range(i + 1, len(numbers)):
        if numbers[i] + numbers[j] == target:
            return (i, j)
```

Correct, `O(n²)` time, `O(1)` space. Nothing is wrong with writing it first —
it is the honest starting point and it makes the improvement concrete.

What it wastes is the scan. For each `i`, the inner loop walks the rest of the
list asking "is any of you `target - numbers[i]`?". That is a **membership
question**, and a list answers membership questions in linear time because it
has no idea what it contains.

## The move

Stop searching for the complement and start *recognising* it.

Standing on `numbers[i]`, the number that would complete the pair is not
something to hunt for — it is `target - numbers[i]`, computable in one
subtraction. The only open question is whether you have already walked past it.

A `dict` answers that in `O(1)`:

```python
seen: dict[int, int] = {}
for index, value in enumerate(numbers):
    complement = target - value
    if complement in seen:
        return (seen[complement], index)
    seen[value] = index
```

`O(n)` time, `O(n)` space. The classic trade: you bought time with memory.

## The two details that are easy to get wrong

**Check before you insert.** If you fill the dict first and then scan it, a
target of `10` with a `5` in the list returns `(i, i)` — the same element
twice. Checking before inserting means the current element is not yet visible
to itself, so the bug cannot happen. That is worth more than a guard clause,
because it is structural rather than remembered.

**Duplicates resolve to the earlier index, for free.** With `[3, 3]` and a
target of `6`, index 0 goes into the dict, index 1 finds it, and you get
`(0, 1)`. `seen[value] = index` overwriting an earlier entry looks like a bug
until you notice that any complement match happens *before* the overwrite.

## What to take away from this one

The pattern generalises well past this problem: **when an inner loop is asking
a membership question, a hash set or dict usually deletes it.** Three-sum,
"find the duplicate", "does a subarray sum to k" (with a running prefix sum)
are all the same move.

The other half is knowing when *not* to. `O(n)` space is free here and
expensive on a stream you cannot fit in memory, and for `n = 20` the nested
loop wins on constant factors and readability. Reaching for the dict
automatically is a different failure from never reaching for it.
