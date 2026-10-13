# A wrapping slice is the whole circle minus a hole

Revealed after grading. This is "Maximum Sum Circular Subarray" (LeetCode 918).

The standard problem has one idea in it: the best slice ending here is either
this value alone or this value added to the best slice ending just before.
The circular version needs one more idea, and it is a change of viewpoint
rather than a new algorithm.

**Look at what a wrapping slice leaves out.** It takes a piece from the end
and a piece from the start, so what it skips is one contiguous stretch in the
middle. To make the wrapping slice as large as possible, make the hole as
small — as *negative* — as possible:

```
best wrapping sum = total - (minimum slice sum)
```

And the minimum slice is the same scan with `max` turned into `min`, so both
run in one pass.

```python
return best if best < 0 else max(best, total - worst)
```

## The case that breaks it

If every value is negative, the minimum slice is the entire list. Then
`total - worst` is `0`: the sum of the *empty* slice, which is larger than any
real answer and is not a slice at all. Every wrong submission to this problem
returns `0` for `[-3, -2, -3]`.

The guard is `best < 0`. A negative best means no single value was
non-negative, which is exactly the all-negative case, and there the ordinary
answer is the only one on offer.

## What the twist was testing

"Now make it circular" is one of the commonest follow-ups there is, and the
reflex answer is to double the list and run the original algorithm over a
sliding window of length `n`. That works and costs a deque and a good deal of
care. Asking *what does the complement look like* is the cheaper question, and
it is worth trying on any problem that gains a wrap-around.
