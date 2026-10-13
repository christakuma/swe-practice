# Binary search needs a question, not a sorted list

Revealed after grading. This is "Peak Index in a Mountain Array"
(LeetCode 852).

A mountain is not sorted and is not a rotation of anything sorted, so the
rotated-array trick — compare the middle with the end, see which half is in
order — has nothing to hold on to. In `[0, 10, 9, 8, 7, 6, 5]` and
`[5, 6, 7, 8, 9, 10, 0]` the middle value is 8 and the end is lower than it
both times, and the peak is on opposite sides.

What binary search actually needs is a yes-or-no question whose answer is
"no, no, no, yes, yes, yes" along the list. Here is one:

> Is this value higher than the next?

On the way up, no. From the peak onwards, yes. The peak is the first "yes".

```python
if numbers[middle] < numbers[middle + 1]:
    low = middle + 1      # climbing: the peak is strictly right
else:
    high = middle         # descending, or standing on it
```

## The two off-by-ones

- `high = middle - 1` throws the peak away when `middle` is it.
- `middle + 1` is safe only because the loop runs while `low < high`, which
  makes `middle < high`. Loop while `low <= high` and it reads past the end.

A purely rising or purely falling list needs no special case: every answer is
"no" or every answer is "yes", and the search ends at the correct edge.

## What the twist was testing

Whether the rotated-array solution was learned as "compare with the end" or
as "find a monotonic question". The first is one problem's trick. The second
is binary search, and it works on things that are not arrays at all — the
smallest capacity that ships everything in ten days, the largest speed that
still finishes on time.
