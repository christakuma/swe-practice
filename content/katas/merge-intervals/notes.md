# Sorting turns a question about a set into a question about one element

Unsorted, "does this interval overlap anything I have already kept?" means
checking it against all of them — and after merging you may have to re-check,
because a merge can make an interval wide enough to reach something it did not
before. That is quadratic and fiddly.

Sort by start, and the question collapses. Every interval you have already kept
begins no later than the current one, so **if the current one does not overlap
the most recent kept interval, it cannot overlap any earlier one either**. One
comparison per interval.

```
sorted:    (1,3) (2,5) (4,8) (7,9)
kept:      (1,3)
           (1,5)   2 <= 3, extend to max(3,5)
           (1,8)   4 <= 5, extend to max(5,8)
           (1,9)   7 <= 8, extend to max(8,9)
```

That is the whole algorithm, and the O(n log n) is the sort — the pass is linear.

## Two details that are the difference between right and nearly right

**`max(last_end, end)`, not `end`.** `[(1, 10), (2, 4)]` is sorted, and (2, 4)
overlaps (1, 10). Extending to the new interval's end *shrinks* the result to
(1, 4). Sorting by start says nothing about ends, so a later interval can be
entirely inside an earlier one.

**`<=` versus `<`, decided rather than defaulted.** With closed intervals,
(1, 3) and (3, 5) share the point 3, so they merge. With half-open intervals —
`[start, end)`, which is how time ranges and array slices usually work — they do
not, and the comparison is `<`. Both are correct for their domain; the mistake
is not noticing there was a choice. If this were a calendar, "the 10:00–11:00
meeting and the 11:00–12:00 meeting" do not conflict, and that is a `<`.

## The family

Sort-then-sweep handles a lot of interval questions, and the only thing that
changes is what you sort by:

| question | sort by | sweep keeps |
|---|---|---|
| merge overlaps | start | the last merged interval |
| do any two overlap? | start | the previous end |
| most intervals you can attend | **end** | the last end taken |
| minimum rooms for all meetings | starts and ends, interleaved | a running count |

The third is the one worth noticing, because sorting by start gives the wrong
answer: the greedy choice for "attend as many as possible" is always the
interval that finishes earliest. Same input, same technique, different sort key,
and the proof of correctness is entirely different.

## Complexity

O(n log n) time, dominated by the sort; the sweep is O(n). O(n) space for the
output, and O(1) beyond it if you merge in place into the sorted list — rarely
worth it, since sorting already allocated.
