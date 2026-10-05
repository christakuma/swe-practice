# Count Bits For Every Number Up To N — the smallest honest DP

Revealed after grading. The problem is the classic one (LeetCode 338); the
wording above is ours. It looks like a bit-manipulation exercise and it is
really a dynamic-programming one, which is the reason it is worth doing: it is
the shortest example where the DP framing is obviously right and costs nothing
to see.

## The obvious answer, and its bound

Call [count-the-set-bits](../count-the-set-bits/notes.md) once per number:

```python
return [count_bits(i) for i in range(n + 1)]
```

Correct, and `O(n log n)` — each call costs up to `log i` steps. For a million
entries that is about twenty million bit operations. Nothing is wrong with it,
and it is the right thing to write first.

## The move

You are filling a table **in order**, which means that when you reach `i`,
every smaller answer is already sitting in the table. So the only question is
which smaller number's answer helps — and shifting gives it to you immediately:

```
i        = 1011 0100
i >> 1   =  101 1010      # i without its lowest bit
i & 1    =            0   # the bit that was dropped
```

The bits of `i` are the bits of `i >> 1` plus the bit you dropped:

```python
counts = [0] * (n + 1)
for i in range(1, n + 1):
    counts[i] = counts[i >> 1] + (i & 1)
return counts
```

`O(n)` time, one constant-time step per entry, no inner loop over bits at all.

## Why one forward pass is enough

`i >> 1 < i` for every `i >= 1`. That inequality is the whole argument: the
read is always strictly behind the write cursor, so the entry being consulted
is always already final. Entry 0 is the base case and needs no special code
because the list starts zeroed and the loop starts at 1.

This is what dynamic programming *is*, stripped of its usual trappings —
**an ordering in which every subproblem is already solved when you need it.**
No memo dict, no recursion, no `@cache`. When a DP problem feels mysterious it
is usually worth asking what this one makes obvious: in what order can I visit
the subproblems so that each one's dependencies are behind me?

## The other recurrence

Reusing the identity from the previous kata:

```python
counts[i] = counts[i & (i - 1)] + 1
```

`i & (i - 1)` clears the lowest set bit, so it is a smaller solved number
exactly one bit lighter. Same bound, same single pass, equally correct. The
shift version is written here because the recurrence reads more directly off
the binary representation; the Kernighan version is the better one if you have
just internalised that trick and want to see it pay off twice.

## The off-by-one

The range is **inclusive**, so the answer has `n + 1` entries. A solution
returning `n` of them agrees with the expected values everywhere it has them,
which is why `test_returns_one_entry_more_than_n` checks the length directly
rather than trusting a value comparison to notice a missing tail.

## What to take away

Two things, and the second is the transferable one.

The bit identity: dropping the lowest bit of a number leaves a smaller number,
which means **any question about a number's bits has a recurrence in terms of a
shift**.

And the DP habit: when you are computing the same family of answers for every
input in a range, stop asking "how do I compute this one" and ask "what does
this one share with one I have already computed". That reframing is what turns
`O(n log n)` into `O(n)` here, and it is the same reframing behind prefix sums,
[climbing stairs](../climbing-stairs/notes.md), and every table-filling
solution in the library.
