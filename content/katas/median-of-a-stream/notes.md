# Median of a Stream — keep only the middle reachable

Revealed after grading. The problem is the classic one (LeetCode 295); the
wording above is ours. It is the last kata in the library and a good one to end
on, because its central idea is the one that runs through most of the others:
**work out what the question actually needs, and store only that.**

## The observation

A sorted list answers `median` in `O(1)` and costs `O(n)` per insertion — it
maintains a total ordering over every element in order to answer a question
about **one or two** of them.

So: never order the whole collection. Split it in half and arrange for the
middle to be the part you can reach.

- a **max-heap** over the low half — its top is the largest small value;
- a **min-heap** over the high half — its top is the smallest large value.

The two candidate middle values are the two heap tops. `median` is `O(1)`,
`add` is `O(log n)`.

## The two invariants

1. every value in `_low` is at most every value in `_high`;
2. `len(_low) - len(_high)` is 0 or 1 — the low half carries the extra element
   on an odd count.

With (2) fixed, `median` needs no arithmetic beyond a parity check: equal sizes
means average the tops, and a longer low half means its top *is* the median.
Pinning which half holds the extra element is what makes that true — allowing
either half to be longer would need a comparison and invites the off-by-one
that returns the lower middle value instead of the average.

## Restoring (1) without comparing anything

The trick worth remembering:

```python
heapq.heappush(self._low, -value)
heapq.heappush(self._high, -heapq.heappop(self._low))
if len(self._high) > len(self._low):
    heapq.heappush(self._low, -heapq.heappop(self._high))
```

Push onto the low half, then immediately move the low half's **top** across.
Whatever the new value was, the largest of the low half ends up on the high
side — so the ordering invariant is restored *by construction*.

The alternative — compare the new value with a heap top and choose a side —
also works and needs a special case for the empty heap, plus a comparison whose
direction is easy to get backwards. The push-then-shuffle version has **no
branches on the way in** at all. Three heap operations instead of one is a
constant factor paid to delete a class of bug.

That is the same preference as the sentinel node in
[merge two sorted lists](../merge-two-sorted-lists/notes.md): make the
structure remove the special case rather than writing the special case.

## The negation

`heapq` is a min-heap only, so the low half stores negated values and its top
is `-_low[0]`. Every sign error in this kata lives in that one convention, which
is why `test_handles_negative_values` exists separately from the general sweep
— negative *inputs* interacting with negated *storage* is where it bites.

## What it must not do

`median` must not pop. A solution that reads its heaps by popping answers
correctly once and then wrongly, which is the kind of bug a single-query test
cannot see — `test_handles_a_single_value_repeatedly_queried` asks three times.

## On verifying it

Checked against `statistics.median` **after every addition**, for every stream
of up to six values over −3..3 — around 140,000 prefixes.

Checking at every prefix rather than at the end is what makes this useful. Both
invariants fail at particular size-and-value combinations, and a final-answer
check would tell you something is wrong without telling you when.

## The pattern this belongs to

A heap is the right answer when a loop's inner step is "give me the
largest/smallest so far" — the same observation as in
[merge k sorted lists](../merge-k-sorted-lists/notes.md). This kata is the
variant where you need **both** ends of the middle, and two heaps facing each
other is the standard construction for it.

Worth knowing the alternatives and why they lose: a balanced BST with subtree
sizes does this and more (any order statistic, not just the median) at the cost
of a real data structure; and if the values are small integers, a count array
with a running total is `O(1)` per add. Both are better in their niche. Two
heaps is the one to reach for when the values are unbounded and the question is
specifically the median.

## What to take away

**Storing less can make a structure faster, not just smaller.** The sorted list
is strictly more informative than the two heaps and strictly worse at this job,
because maintaining information you do not need is work you have to do on every
update. Asking "what is the least I could store and still answer this?" is a
better opening question than "which data structure should I use?".
