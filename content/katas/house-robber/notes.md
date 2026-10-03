# Why greedy fails, concretely

The instinct is a pattern: take the odd positions, or the even ones, or
repeatedly take the largest remaining value and cross out its neighbours. Each
is wrong, and each has a short counter-example.

**Alternate.** `[5, 1, 1, 5]`. Positions 0 and 2 give 6; positions 1 and 3 give
6; the answer is 10, taking the two ends — a gap of *two*, which no alternating
pattern produces.

Note what this does not mean: alternating is often optimal. `[2, 7, 9, 3, 1]`
wants positions 0, 2 and 4. There is simply no rule about gaps that holds in
both cases.

**Take the largest, cross out its neighbours, repeat.** This one is genuinely
convincing. It gets `[3, 10, 3, 10, 3]` right — both 10s, for 20 — and fails on
`[6, 5, 5, 6, 5, 5, 6]`: it takes the three 6s for **18**, while taking every
other value gives 6 + 5 + 5 + 6 = **22**. Grabbing the largest value forced it
to skip two 5s that were worth more together than the 6 it gained.

The pattern in the failures is the same: the right choice at a position depends
on what the best answer for the whole prefix was, and no amount of local
information substitutes. That dependency is the signature of dynamic programming
rather than greed.

## The recurrence

```
best(i) = max( best(i - 1),              skip value i
               best(i - 2) + values[i] ) take value i
```

Taking value `i` forbids `i - 1` but says nothing about anything earlier, so the
best compatible total is `best(i - 2)`. The two cases are exhaustive — you take
it or you do not — and each reduces to a strictly smaller subproblem.

Two base cases: `best(-1) = 0` and `best(-2) = 0`, which is what the two
variables are initialised to. Both zero, because the empty row yields nothing.

## The two-variable form, and its one trap

```python
take, skip = skip + value, max(skip, take)
```

`take` = the best total that **uses** this value; `skip` = the best that does
not. Both new values depend on both old ones, which is why the tuple assignment
matters: updating `take` first and then reading it for `skip` uses the new value
and silently permits adjacency.

That is the kind of bug that passes `[1, 2, 3]` and fails on longer inputs,
which is why the suite has a long run of equal values — `[4, 4, 4, 4, 4]` must
be 12, and a solution with the ordering bug reports 20.

## Variants worth knowing

- **houses in a circle** — the first and last are now adjacent. Run the linear
  version twice, once excluding the first house and once excluding the last, and
  take the better. Two O(n) passes, no new ideas.
- **no three adjacent** — allowed to take two in a row but not three. The state
  grows: you need to know how many you have taken consecutively, so the
  recurrence has more cases rather than a longer reach.
- **a tree instead of a row** — the same take/skip decision at each node, with
  the children's answers combined instead of the previous two. Same shape, and
  it is where the "two variables" collapse stops being available.
