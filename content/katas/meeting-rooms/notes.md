# Only the room that frees up soonest is worth checking

Sort by start, and keep the end times of the meetings currently in progress in a
min-heap. For each new meeting:

- if the earliest end time is at or before this start, that room is free → reuse
  it
- otherwise every room is busy → open a new one

The heap's size at the end is the answer, because it only ever grows: it is a
high-water mark of simultaneous meetings.

**Why one room is enough to check**: the heap's minimum is the *earliest* any
room becomes free. If that one is still occupied, none of the others can be. So
there is no search and no choice — which is what makes the greedy correct rather
than merely plausible.

```
[(0, 30), (5, 10), (15, 20)]   sorted by start

(0, 30)   heap [30]            open a room
(5, 10)   heap [10, 30]        30 > 5, so open another
(15, 20)  heap [20, 30]        10 <= 15, reuse that room
answer 2
```

## The heap is answering one question

A list, scanned for its minimum, is the same algorithm at O(n²). The heap makes
each step O(log n), so the whole thing is O(n log n) — the same cost as the sort
it already pays, which is the sign that the data structure is the right size for
the job rather than overkill.

## The sweep, which needs no heap

```python
starts = sorted(s for s, _ in meetings)
ends   = sorted(e for _, e in meetings)
```

Walk the two sorted lists together: a start increments a counter, an end
decrements it, and the answer is the maximum the counter reaches. Same
complexity, less machinery, and genuinely elegant.

What it loses is **which room each meeting is in**. The heap version can be
extended to assign room numbers, because each heap entry *is* a room; the sweep
only ever knows how many are busy. Which one to reach for depends on whether
"how many" or "which" is the real question — and in a calendar application it is
always "which".

## `<=` versus `<`, again

These intervals are half-open — `[start, end)` — so a meeting ending at 3 does
not overlap one starting at 3, and the comparison is `ends[0] <= start`. With
`<`, three back-to-back meetings need three rooms.

[merge-intervals](../merge-intervals/notes.md) takes the opposite convention:
its intervals are closed, so touching counts as overlapping. Same one-character
decision, opposite answers, and both exercises state it in the prompt because
there is no way to infer it.

The real-world reading is the useful one: a 10:00–11:00 meeting and an
11:00–12:00 meeting do not conflict. Time ranges are nearly always half-open,
and so are array slices, for the same reason — adjacent ranges tile without
overlap and without gaps.

## The neighbouring problems, with different sort keys

| question | sort by | greedy rule |
|---|---|---|
| fewest rooms | start | reuse the soonest-free room |
| most meetings one room can host | **end** | take the meeting that finishes first |
| do any two overlap at all? | start | compare each start to the previous end |

The middle one is the interesting contrast: for "attend as many as possible",
sorting by start gives the wrong answer, and the correct greedy choice is always
the meeting that *ends* earliest. Same inputs, same technique, different key,
and a completely different proof of correctness.
