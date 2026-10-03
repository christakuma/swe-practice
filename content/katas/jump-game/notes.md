# The reachable set is always a prefix, so one number describes it

A jump of length `n` from position `i` may land anywhere from `i + 1` to
`i + n` — **including every position in between**. So the set of reachable
positions is never patchy; it is always a contiguous prefix, and one number
describes it: how far it extends.

```python
furthest = 0
for index, jump in enumerate(jumps):
    if index > furthest:
        return False          # unreachable, and so is everything after it
    furthest = max(furthest, index + jump)
return True
```

That is why greedy is correct here, and the reasoning is worth having rather
than the result: there is **no choice to make**. You are not picking jump
lengths; you are computing a frontier. Problems where greedy is wrong — like
[knapsack](../knapsack/notes.md) or
[house-robber](../house-robber/notes.md) — are the ones where a local choice
forecloses a better global one. Here nothing is foreclosed.

The DP version keeps a reachable flag per position and is O(n²) for no benefit.
Worth writing once to see that the extra information it computes is never used.

## The two ends

Both edge cases in this problem are about the last position:

- **`[0]`** → True. You start at the end; no jump is needed.
- **`[1, 0]`** → True. The zero is *at* the destination, so its jump length is
  irrelevant. A solution that insists the final jump be positive gets this
  wrong, and it is the common mistake.

The loop above handles both without a special case, because `furthest` is
compared against the index you are standing on rather than against the end. A
version written as "can I jump beyond the last index" needs an off-by-one at the
boundary and usually has one.

## Jumping over a zero

`[2, 5, 0, 0]` is True: from position 0 you can jump 1 to reach the 5, and from
there 5 clears everything. A solution that stops at the first zero is thinking
of each value as "the exact distance" rather than "at most". The suite tests it,
because every other case gives the same answer either way.

## The follow-ups

**Fewest jumps to reach the end** is the same shape with one more variable:
track the current jump's frontier *and* the next one, incrementing a counter
when you run out of the current range. Still O(n), still greedy, and still
correct for the same prefix reason.

**Can you reach position k, moving either direction?** is no longer a prefix —
it is a graph reachability question and needs BFS. That is the dividing line:
the one-number frontier works only because movement is forward-only, and the
moment you can go backwards the reachable set becomes patchy and one number
cannot describe it.
