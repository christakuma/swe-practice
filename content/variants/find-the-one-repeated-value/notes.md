# The list is already a linked list

Revealed after grading. This is "Find the Duplicate Number" (LeetCode 287).

The standard problem is solved by remembering what you have seen. Take the
memory away and forbid rearranging the list, and both obvious approaches are
gone: no set, and no sorting in place. What is left is the one unusual fact
about the input — **every value is a valid position**.

So let each entry point at the position its value names:

```
position:  0  1  2  3  4
value:     1  3  4  2  2        0 -> 1 -> 3 -> 2 -> 4 -> 2 -> 4 -> ...
```

Nothing holds the value 0, so nothing points at position 0: it is the head of
a tail. Positions 3 and 4 both hold a 2, so two arrows arrive at position 2.
A node with two arrows in is where a tail joins a loop, and its index is the
repeated value.

That is "Where the Loop Begins", run on indices instead of nodes: slow and
fast until they meet, then one pointer from the start and one from the meeting
point, in step, until they meet again.

## Why arithmetic does not do it

`sum(numbers) - n * (n + 1) // 2` is the first thing to try and is correct
when the list is `1..n` plus one extra copy. The problem does not promise
that. A value appearing three times displaces another value entirely, and
`[2, 2, 2, 2, 2]` sums to the "wrong" 10 with no way to tell which shortfall
came from where. XOR fails the same way.

There is a second honest solution: binary search on the *value*. Count how
many entries are at most `m`; if more than `m`, the repeat is at most `m`.
That is `O(n log n)` time, `O(1)` space, reads only, and passes.

## What the twist was testing

Whether a constraint that looks like bookkeeping — "each between 1 and n" —
gets read as a gift. Problems that take away your usual tool almost always
hand you a replacement in the small print.
