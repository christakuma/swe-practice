# Move one bit up, drop the rest to the floor

Revealed after grading. This trick is usually called Gosper's hack; it is how
you enumerate every subset of a fixed size as a bit mask.

Counting the 1 bits is something you do *to* a number. This asks you to
understand what the count allows: which rearrangements of the same bits are
larger, and which of those is smallest.

## The move

To get larger, some 1 has to move up into a 0. To get larger by as little as
possible, use the lowest place where that can happen: the top of the lowest
block of 1s, which has a 0 directly above it.

```
n       = 1 0 1 1 1 0 0
                ^-----^      lowest block
ripple  = 1 1 0 0 0 0 0      n + lowest: the block carries
answer  = 1 1 0 0 0 1 1      the other two 1s go to the bottom
```

After the carry, everything below the moved bit is zero and `k - 1` ones are
owed. They go at the very bottom, because that makes the smallest number.

## The arithmetic

```python
lowest = n & -n
ripple = n + lowest
return ripple | ((n ^ ripple) >> 2) // lowest
```

`n ^ ripple` is a run of `k + 1` ones: the block, plus the bit the carry
landed on. Two fewer are wanted, so shift right by two. Dividing by `lowest`
— a power of two — shifts the run down to bit zero.

## The plausible half-answer

Swapping the lowest `01` to `10` and stopping there is larger and has the
right count. For `0110` it gives `1010`, which is 10; the answer is `1001`,
which is 9. The leftover ones were not pushed down.

## What the twist was testing

That `n & -n` and "add the lowest bit" are tools and not incantations. The
standard problem uses `n & (n - 1)` to delete the lowest 1; this is its
sibling, and both come from watching what a borrow or a carry does to the
bottom of a number.
