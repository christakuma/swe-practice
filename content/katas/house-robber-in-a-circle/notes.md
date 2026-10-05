# House Robber in a Circle — reduce, don't extend

Revealed after grading. The problem is the classic one (LeetCode 213); the
wording above is ours. It exists to teach one habit: **when a problem is a
solved problem plus one constraint, case-split on the constraint rather than
extending the recurrence.**

## The temptation

The circle makes the first and last houses adjacent. The instinct is to carry
that through the recurrence — track whether the first house was taken, so the
last one can consult it:

```python
# two parallel DP states, one per decision about house 0...
```

It works and it roughly doubles the code, and the state you have added is a
fact about the *input's edge*, not about the subproblem — which is why it feels
awkward the whole way through.

## The move

The circle adds **exactly one** rule. So split on it:

> Any valid answer either omits the first house or omits the last. It cannot
> include both.

Those two cases are exhaustive, and each one is a **straight line** — the
problem you already solved:

```python
return max(_straight_line(houses[1:]), _straight_line(houses[:-1]))
```

Two linear passes instead of one: a constant factor, in exchange for reusing a
function you already trust instead of writing one you do not.

The general shape is worth keeping. A constraint that relates only the two
*ends* of a structure is usually better handled by enumerating the few ways it
can be satisfied than by threading it through every step.

## The overlap is fine, and would not always be

The two cases overlap: an answer omitting **both** the first and last houses is
counted twice.

That is harmless here, because `max` does not care about double-counting — only
about missing something. Had the question been *how many* ways, the same split
would be wrong and would need inclusion–exclusion.

**"Exhaustive but overlapping" is fine for an optimum and fatal for a count.**
Worth checking which you have before reusing a split; it is the difference
between this kata and [count the decodings](../count-the-decodings/notes.md),
where the two cases must be disjoint.

## The single house

The one input where both slices are empty, so the split reports `0` instead of
the house's value. Guarded before the split, which is cheaper than making the
slices clever.

Same category as the seeds in `count-the-decodings`: **the base case of the
reduction and the answer for the smallest input can disagree**, and when they
do, the guard is the honest fix rather than a sign the reduction is wrong.

## The wrap-around is easy to forget in your own test cases

`best_haul([5, 0, 0, 5])` is `5`, not `10`. Two fives with two zeros between
them — and in a circle of four, positions 0 and 3 are still neighbours. The
intervening zeros make it look safe.

That expected value was written as `10` here and caught by the content suite,
which is the honest version of a recurring lesson in this batch: for a problem
whose whole point is a constraint you are not used to, your intuition about
examples is **exactly** the thing under test. Every literal in the suite was
re-checked against the subset-enumerating oracle afterwards.

## The straight-line recurrence, for completeness

```python
taken = skipped = 0
for amount in houses:
    taken, skipped = skipped + amount, max(skipped, taken)
return max(taken, skipped)
```

`taken` is the best total **ending with this house used**; `skipped` is the best
**without** it. Taking a house adds to the best that excluded its predecessor,
which is what enforces non-adjacency without any index arithmetic.

## What to take away

**Look for the reduction before reaching for a bigger state.** More DP state is
the obvious response to a new constraint and usually the worse one: it is
harder to reason about, harder to test, and it throws away a function that
already works. Two calls and a `max` is a better answer than a cleverer
recurrence.
