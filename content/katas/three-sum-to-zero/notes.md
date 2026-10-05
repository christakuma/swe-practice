# Three Sum to Zero — sorting buys two different things

Revealed after grading. The problem is the classic one (LeetCode 15); the
wording above is ours. It is the first kata in this library where
**deduplication is the hard part**, and that is the half worth studying — the
search itself is a two-pointer walk you have probably seen.

## Fix one, two-sum the rest

Three nested loops is `O(n³)`. Fix the first value and the remainder is a
two-sum over the suffix for a known target, so the real question is how fast
that inner two-sum can be.

[Two sum](../two-sum/notes.md) answered it with a dict in `O(n)` — which would
work here and gives `O(n²)` overall. But on **sorted** data you do not need the
dict at all:

```python
low, high = first + 1, size - 1
while low < high:
    total = numbers[first] + numbers[low] + numbers[high]
    if total < 0:
        low += 1          # only way to increase the sum
    elif total > 0:
        high -= 1         # only way to decrease it
    else:
        record(); low += 1; high -= 1
```

Each step eliminates one candidate permanently, so the inner scan is linear and
the whole thing is `O(n²)` with `O(1)` extra space. The dict version is the
same time bound and `O(n)` space — the two-pointer walk is strictly better once
you have paid for the sort.

## What the sort actually buys

Two things, and conflating them is why this problem feels fiddly:

1. **Searchability from both ends.** The monotonicity is what makes "too low →
   move left pointer right" a valid deduction rather than a guess.
2. **Duplicates become adjacent.** Which turns "have I already produced this
   triple?" into a comparison with the neighbour, rather than a lookup in a set
   of everything produced so far.

`O(n log n)` for both, inside an `O(n²)` budget. Free.

## The three skips, and why there are three

This is the part people get wrong, usually by fixing one of them and assuming
the others follow.

```python
if first > 0 and numbers[first] == numbers[first - 1]:
    continue                                   # (1) the fixed value
...
    low += 1; high -= 1
    while low < high and numbers[low] == numbers[low - 1]:
        low += 1                               # (2) after a hit
    while low < high and numbers[high] == numbers[high + 1]:
        high -= 1                              # (3) after a hit
```

**(1)** A repeated first element can only re-find triples the earlier copy
already found — its suffix is a subset of the earlier one's.

**(2)** and **(3)** A recorded triple would be rebuilt identically by any other
copy of the same two values, so both pointers must move past their duplicates.

The distinction that makes this hard is between **repeated values** and
**repeated triples**. `[-1, -1, 2]` must return `(-1, -1, 2)` — using `-1`
twice is legal because the list holds it twice. `[-1, -1, -1, 2, 2, 2]` must
return it exactly **once**. A rule that forbids reusing a value drops the
first; a rule that forbids nothing produces the second several times. The skips
get both right because they are about *positions already considered*, not about
values.

`test_requires_three_distinct_positions` and
`test_uses_a_repeated_value_when_there_are_enough_copies` are deliberately
adjacent in the suite for this reason — they pull in opposite directions and a
solution has to satisfy both.

## Skipping versus a set

```python
found = set()
...
found.add((a, b, c))
return sorted(found)
```

Correct, shorter, and a perfectly defensible answer. The costs: it allocates in
proportion to the number of *candidate* hits rather than distinct ones, and it
conceals why the duplicates arise in the first place. If you reach for the set
you never have to understand the multiplicity structure — which is fine until
the next problem in the family (four-sum, k-sum) where the skips are the only
thing keeping the constant factor sane.

Worth having both. The set version is what to write under time pressure; the
skips are what to understand.

## The break is load-bearing

```python
if numbers[first] > 0:
    break
```

Once the fixed value is positive, the whole suffix is positive too — the list
is sorted — so no triple starting here can reach zero, and every later fixed
value is worse. This is not a micro-optimisation: on a list of mostly positive
values it turns the quadratic scan into a short one, and it is the same kind of
reasoning as the inner pointer moves. *Sortedness lets you rule out a whole
region from one comparison.*

## What to take away

**Two pointers from both ends is the sorted-data counterpart of a hash map.**
When you have already paid for a sort, prefer it: same time bound, `O(1)` space,
and it generalises to "closest to a target" and "count the pairs below a
threshold", which a dict does not.

And when a problem says "distinct results", **work out whether the duplicates
come from repeated values or repeated positions before you write any
deduplication.** The two need different rules, and a test suite that only
contains one kind will happily bless the wrong one.
