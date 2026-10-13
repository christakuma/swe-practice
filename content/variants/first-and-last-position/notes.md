# Search for the boundary, not the value

Revealed after grading. This is "Find First and Last Position of Element in
Sorted Array" (LeetCode 34).

The rotated-array search was hard because the list was not sorted. This list
is sorted and the difficulty has moved: the target is not *a* position any
more. It is a run, and binary search as usually written stops at whichever
copy it happens to land on.

The repair is to stop searching for the value and search for an **edge**:

> the first position whose value is `>= target`

There is exactly one such position, repeats or no repeats. The loop that
finds it never has an "equal, so return" branch:

```python
while low < high:
    middle = (low + high) // 2
    if numbers[middle] < value:
        low = middle + 1
    else:
        high = middle
```

Equal goes into the `else`: "the answer is here or to the left". That is the
whole difference from textbook binary search, and it is what `bisect_left`
is.

The end of the run is the same search asked about `target + 1`, minus one.
(For non-integers, write a second loop with `<=` — that is `bisect_right`.)

## Why not find one and walk?

Binary search to any copy, then step left and right until the value changes.
It is correct, and when the run is a million long it reads a million values.
The `O(log n)` guarantee was about the size of the *list*; the walk makes it
depend on the size of the *answer*.

## What the twist was testing

That binary search is a tool for finding where a yes/no question flips, and
"is it equal?" is not such a question — it goes no, yes, no. "Is it at
least?" goes no, no, yes, yes. Nearly every use of binary search outside
textbooks is the boundary form, and it has no early return.
