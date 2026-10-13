# One comparison, many triples

Revealed after grading. "3Sum Smaller" (LeetCode 259).

Three-sum finds triples that hit a target exactly, and each step of its two
pointers finds at most one. Here a single comparison can account for
hundreds.

```python
if ordered[first] + ordered[low] + ordered[high] < target:
    count += high - low
    low += 1
else:
    high -= 1
```

## Why `high - low`

The list is sorted. If `first`, `low` and `high` sum to less than the
target, then swapping `high` for anything between `low` and `high` makes the
sum no bigger. So `low` pairs with *every* position from `low + 1` to `high`:
that is `high - low` triples.

Having counted all of `low`'s partners, `low` is done. Move it up.

If the sum is not small enough, `high` is too big — for this `low` and, since
later `low`s are larger, for all of them. Move it down.

## Why it has to be done this way

The answer for two thousand zeros and a target of 1 is 1,331,334,000. No
loop that executes once per qualifying triple finishes. The count has to be
assembled from pieces bigger than one, and `high - low` is that piece.

This is the general shape of counting with two pointers: when the pointers
establish a fact about one pair, monotonicity extends it to a range, and you
add the size of the range.

## Do not skip duplicates

Three-sum steps past repeated values so it does not report the same triple
twice. That reflex is wrong here. `[1, 1, 1, 1]` has one distinct triple of
values and four choices of positions, and the question asks for four.

## Sorting is allowed

The question is "how many sets of three positions", which does not care
where the positions are. Sorting rearranges the list without changing how
many triples sum to anything. (Sort a copy; the caller's list is theirs.)

That would not be true if the question asked for positions `i < j < k` with
some condition on the *order* of values. Whether sorting preserves the thing
being counted is always worth a sentence.

## What the twist was testing

Moving from finding to counting. The setup is identical — sort, fix one,
two pointers — and the temptation is to keep the body of the loop too:
check, record, move both. Counting rewards a different question at each
step: not "is this a hit?" but "how many hits does this one comparison
settle?"
