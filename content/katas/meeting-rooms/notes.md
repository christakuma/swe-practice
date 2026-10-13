# After sorting, only neighbours can clash

Revealed after grading. This is the classic "Meeting Rooms" (LeetCode 252); the
wording above is ours.

Two half-open meetings overlap when each starts before the other ends:

```python
a_start < b_end and b_start < a_end
```

Checking that for every pair is the definition, and it is `O(n^2)`. The whole
exercise is noticing that most of those pairs never need looking at.

## The move

Sort by start time. Now suppose some meeting overlaps one that is *not* next to
it in that order. Everything between them starts no later than the far one does
— so it starts before the near one ends as well. The near meeting already
clashes with its own neighbour.

That is the claim: **if any two meetings clash, two adjacent ones do.** So one
pass over neighbours answers the question.

```python
ordered = sorted(meetings)
return all(nxt[0] >= prev[1] for prev, nxt in pairwise(ordered))
```

`O(n log n)` for the sort and `O(n)` for the pass.

## The two details

**`>=`, not `>`.** The intervals are half-open, so a meeting that starts at 3
when the previous one ends at 3 is fine. Writing the comparison the strict way
round is the characteristic bug here, and it is invisible on any test that does
not contain two meetings that touch.

**`sorted`, not `.sort()`.** The function is asked a yes-or-no question about
someone else's list. Reordering it in place answers the question and leaves the
caller holding a different list than they passed in — the kind of side effect
that costs an afternoon somewhere far from here.

## Why this one comes before the room count

`how-many-meeting-rooms` asks the harder question — not *is there* a clash, but
*how many* meetings run at once at the worst moment — and this kata is the
special case where that answer is at most one. The sort is the same. What
changes is that a yes-or-no only needs the previous meeting's end, where a
count needs the ends of everything still in progress, which is where the heap
comes from.

The pattern to keep: **when a question is about overlapping intervals, sort
them first and ask what the order now guarantees.** Merging, inserting,
counting rooms and removing the fewest all start there.
