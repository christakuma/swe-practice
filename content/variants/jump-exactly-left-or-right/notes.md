# When the reachable set stops being an interval

Revealed after grading. This is "Jump Game III" (LeetCode 1306).

The standard problem has a famously short solution: carry one number, the
furthest position you can reach, and check you never fall behind it. That
works because of something easy to overlook — a jump of *up to* `n` reaches
every position on the way, so the reachable positions are always one solid
block from the start to the frontier. One number describes a block.

Two changes here, and either one alone breaks that:

- **Exact jumps** skip the positions in between. From 0 you may reach 3 and
  6 and nothing else.
- **Leftward jumps** mean the frontier is no longer the interesting edge.

The reachable set is now an arbitrary scatter of positions, and no single
number summarises it. It has to be found the general way.

## It is a graph

Each position is a node with up to two edges. "Can I get from `start` to a
node with a zero?" is reachability:

```python
seen = [False] * len(jumps)
pending = [start]
...
for landing in (position - jumps[position], position + jumps[position]):
    if 0 <= landing < len(jumps) and not seen[landing]:
```

Depth-first or breadth-first makes no difference to the answer. What does
matter is `seen`: `[2, 0, 2]` sends 0 to 2 and 2 to 0 for ever.

## What the twist was testing

Whether you knew *why* the greedy scan was valid. It is one of the neatest
solutions in the whole library and it rests entirely on the reachable set
being contiguous. Interview follow-ups to greedy solutions nearly always
remove the property that made greed safe, and the honest fallback is the
general search the greedy solution was a shortcut for.
