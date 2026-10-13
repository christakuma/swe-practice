# Halve, sort, merge — the reorder outline with a different last step

Revealed after grading. "Sort List" (LeetCode 148).

Reordering a list was: find the middle, reverse the back half, weave. This
is: find the middle, sort each half, merge. The first step is the same code.

## Why merge sort

An array can be sorted in a dozen ways because you can jump to any position.
A linked list can only walk forward and splice. Merge sort needs nothing
else:

- **split** — one walk with two pointers;
- **merge** — walk two lists once, splicing the smaller front node.

Quicksort wants to swap across a distance; heapsort wants indices.
Insertion sort works, and is quadratic.

## The split

```python
slow, fast = head, head.next
while fast is not None and fast.next is not None:
    slow = slow.next
    fast = fast.next.next
second = slow.next
slow.next = None
```

Two details, both of which fail loudly:

- **`fast` starts one ahead.** With two nodes, `slow` must stop on the first
  so that each half gets one. Start them together and `slow` ends on the
  second node: the second half is empty, the first half is the whole list,
  and the recursion never gets smaller.
- **`slow.next = None`.** Finding the middle does not separate anything.
  Without the cut, the "first half" still runs to the end.

## The merge

```python
if second.value < first.value:
    take from second
else:
    take from first
```

Strictly less. On a tie the node from `first` goes in, and everything in
`first` came earlier in the original list than everything in `second`. That
one choice of `<` over `<=` is what makes the sort stable.

## Recursion, safely

Recursing *along* a list is one frame per node, which Python refuses past a
thousand. This recurses on *halves*: fifty thousand nodes is sixteen levels.
The depth is what matters, not the number of calls.

(A bottom-up version — merge runs of 1, then 2, then 4 — uses no stack at
all and is the answer to "can you do it in constant space?". It is fiddlier
and the same idea.)

## Why not just use a list

```python
nodes = collect(head)
nodes.sort(key=lambda node: node.value)
relink(nodes)
```

That is correct, stable, fast, and what you would write at work. It is ruled
out here for the same reason the reorder problem ruled it out: it turns the
linked list into an array and solves the array problem. The memory test is
there to hold that line — fifty thousand pointers is 400 kilobytes, and the
relinking version needs a few hundred bytes.

## What the twist was testing

Recognising a familiar skeleton. "Find the middle, deal with the halves,
combine" came up in the reorder problem as three unrelated-looking tricks.
Here it comes back as divide and conquer, and the candidate who saw the
structure the first time has one new piece to write — the merge — and
already knows where the middle is.
