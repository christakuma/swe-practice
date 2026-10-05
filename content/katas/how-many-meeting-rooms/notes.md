# How Many Meeting Rooms — stop thinking about rooms

Revealed after grading. The problem is the classic one (LeetCode 253); the
wording above is ours. The title is the trap: it asks about rooms, and the
answer has nothing to do with assigning anything to anything.

## The reframing

> The number of rooms needed is the largest number of meetings running at the
> same moment.

That is a property of the **timeline**, not an assignment problem. Once you see
it that way, no meeting is ever placed anywhere, there is nothing to pack, and
the greedy "which room should this go in?" question — which has no obvious
answer — never comes up.

Proving it is easy in both directions: you clearly need at least the peak
number of rooms, and you never need more, because you can always put a meeting
in whichever room is free at the moment it starts.

**This is the move the problem is for: a question phrased as an assignment is
often a question about a maximum.** Same shape as flipping "remove the fewest"
into "keep the most" in
[fewest intervals to remove](../fewest-intervals-to-remove/notes.md) — both
replace a choice you cannot make locally with a quantity you can just count.

## The sweep

The count only changes when something starts or ends, so only those moments
matter:

```python
starts = sorted(start for start, _ in meetings)
ends = sorted(end for _, end in meetings)

running = peak = finished = 0
for start in starts:
    while finished < len(ends) and ends[finished] <= start:
        running -= 1
        finished += 1
    running += 1
    peak = max(peak, running)
return peak
```

`O(n log n)` for the sorts, one pass after.

The two lists are **decoupled**: a start and the end it belongs to are never
looked at together. That feels wrong the first time and is the whole point —
the identity of the meeting is irrelevant to *how many* are running. Letting go
of the pairing is what removes the need for a heap.

## The heap version, and why it is not better

The model most people reach for: sort by start, keep a min-heap of end times,
pop everything that has finished before pushing the new end. The heap's size is
the room count.

```python
for start, end in sorted(meetings):
    if heap and heap[0] <= start:
        heapq.heappop(heap)
    heapq.heappush(heap, end)
    peak = max(peak, len(heap))
```

Also `O(n log n)`, also correct, and it is the version to write if it comes to
mind first. It is doing strictly more work than the question requires: it
tracks *which* meetings are running when only the count is wanted. The sweep is
the same algorithm with that information discarded.

Worth having both, and worth noticing the pattern: **when a heap is only ever
asked for its size, you probably do not need the heap.**

## Ends before starts on a tie

A meeting ending exactly when another begins shares a room, so at an equal
timestamp the `-1` must be applied first. That is `ends[finished] <= start`,
and `<` instead counts touching meetings as overlapping —
`rooms_needed([(1, 2), (2, 3)])` reports 2.

Third kata in a row where one character of an endpoint comparison is the whole
behaviour, and the third different consequence: in
[insert an interval](../insert-an-interval/notes.md) touching intervals
**merge**, in `fewest-intervals-to-remove` they **coexist**, and here they
**share a room**. The convention is the same each time; what changes is the
operation. Reading the prompt beats remembering the comparison.

## The guard that cannot trigger

```python
while finished < len(ends) and ...
```

For in-contract input this bound is unreachable — every meeting has positive
duration, so something is always still running when the next one starts. It is
there because a zero-width meeting, which the prompt excludes, walks the
pointer off the end and raises `IndexError`.

Found by running the exhaustive check with degenerate intervals in the pool.
**A guard that costs one comparison and turns a crash into a defensible answer
is worth keeping even when the contract forbids the input** — the contract
protects the caller, not the function.

## What to take away

**Ask what quantity the answer actually is.** "How many rooms" sounds like
scheduling and is a maximum; "which meetings to drop" sounds like selection and
is a maximisation of what stays. Interval problems are unusually prone to this,
because the physical story suggests an algorithm and the mathematical question
is almost always simpler than the story.
