# One number: when is everyone free?

Revealed after grading. The "find a free slot" question, which usually
follows "Meeting Rooms" (LeetCode 252).

"Can one person attend them all?" assumed the meetings should not overlap
and asked whether they do. This starts from a diary that overlaps freely and
asks where the holes are.

## The sweep

Sort by start and carry `free_from`: the earliest moment at which everything
looked at so far is over.

```python
free_from = opens
for start, end in sorted(meetings):
    if start - free_from >= duration:
        break
    free_from = max(free_from, end)
return free_from if closes - free_from >= duration else None
```

Between `free_from` and the next meeting's start, the diary is empty:
nothing earlier reaches that far, and nothing later starts that soon. The
first such gap that is long enough is the answer, and the earliest, because
the walk goes forward in time.

## `max`, not assignment

```
9 ─────────────── 12
     10 ── 11
```

`free_from = end` sets it to 11 after the second meeting — inside the first.
The diary is free from 12. A sorted list is ordered by *start*; the ends can
be in any order at all.

This is the same line that merges overlapping intervals, and it is the line
that "can you attend them all?" never needed, because there an overlap ended
the question.

## The edges of the day

- **Opening.** `free_from = opens`. A meeting that ended before the day began
  leaves it alone (`max`); one still running pushes it forward. A gap that
  started before opening is measured from opening, because that is where
  `free_from` is.
- **Closing.** One test at the end. If the loop broke at a gap, the gap must
  still finish by `closes`. If the loop ran out of meetings, the stretch
  from `free_from` to `closes` is the last gap — and forgetting it is the
  commonest bug in this problem.

## Half-open

`>=`, twice. A gap exactly as long as the meeting is long enough: the new
meeting starts as one ends and ends as the next starts, and touches neither.

## What the twist was testing

Turning a yes-or-no check into a search without starting again. The sort is
the same; the scan is the same; what is new is deciding what to *remember*
between meetings. One number is enough, and saying precisely what that
number means — "everything so far is over by now" — is what makes the `max`
and both edge cases obvious instead of things to be debugged.
