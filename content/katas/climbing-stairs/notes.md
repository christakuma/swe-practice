# Ask what the last move was

That one question turns most counting problems into a recurrence. Here, the last
step was either a single or a double:

```
ways(n) = ways(n - 1)      the routes that finish with a single step
        + ways(n - 2)      the routes that finish with a double
```

The two sets are **disjoint** (a route finishes one way or the other, not both)
and **exhaustive** (there is no third kind of step), which is exactly what lets
the counts add. Both halves have to be true, and checking them is the difference
between deriving a recurrence and guessing one.

It is Fibonacci, which is worth noticing *after* deriving it rather than
instead.

## `ways(0) = 1` is the whole base case

There is one way to climb no steps: take none. Writing 0 there makes every
answer 0 — nothing can be built from nothing — and `ways(2)` is the shortest
input that shows it: both `1+1` and `2` are real routes, and the second one is
"arrive from step 0".

The pattern recurs across counting problems: the empty case is usually **one**
way, not none. One way to make change for 0 (use no coins), one subset of an
empty set, one path of length zero. Getting it wrong zeroes out everything
downstream, which at least fails loudly.

## Three implementations of the same recurrence

```python
# 1. naive recursion: O(2^n)
def ways(n):
    if n <= 1:
        return 1
    return ways(n - 1) + ways(n - 2)

# 2. memoised: O(n) time, O(n) space, O(n) stack
@functools.cache
def ways(n): ...

# 3. bottom-up, two variables: O(n) time, O(1) space, no stack
previous, current = 1, 1
for _ in range(steps):
    previous, current = current, previous + current
return previous
```

The first is exponential because `ways(n - 2)` is computed twice at every level,
and that duplication compounds. It is the canonical demonstration of why
memoising matters at all, and it is worth writing once and timing.

The third is what "space-optimised dynamic programming" means in practice: the
recurrence reads back exactly two places, so keep two variables rather than a
table of n. It also has no recursion, which matters at n = 500 where the
memoised version is 500 stack frames deep on its first call.

## Order matters, and the alternative problem

`1+2` and `2+1` count separately, so this counts **sequences**. The problem that
counts *combinations* of step sizes — how many multisets of 1s and 2s sum to n —
is a different and genuinely harder recurrence, and gives 3 for n = 4 rather
than 5.

That distinction is the first thing to pin down in any counting problem, because
the two answers diverge immediately and neither is wrong without the
specification.

## Where it generalises

Steps of size 1, 2 or 3 → three terms, same shape. Steps from an arbitrary set →
sum over the set, which is **coin change** counting arrangements. Forbidden
steps → the same recurrence with some terms dropped, which is
[house-robber](../house-robber/notes.md) wearing a different story. Recognising
the family is worth more than the Fibonacci.
