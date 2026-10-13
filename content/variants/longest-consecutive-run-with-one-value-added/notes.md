# One wildcard, and where it is worth most

Revealed after grading. A follow-up to "Longest Consecutive Sequence"
(LeetCode 128): the same problem with one free value.

## What the extra value can do

Three things, and the first two are the same:

- sit just **above** a run — the run plus one;
- sit just **below** a run — the run plus one;
- sit in a **gap of exactly one** between two runs — both runs, plus one.

So the answer is at least "longest run + 1", and the only question is
whether some gap does better.

## The second walk

The standard solution walks up from the bottom of each run:

```python
if value - 1 in present:
    continue            # not the bottom of a run
end = value
while end + 1 in present:
    end += 1
```

When that loop stops, `end + 1` is missing. Pretend it is the value you add,
and keep going from the other side of it:

```python
beyond = end + 2
while beyond in present:
    beyond += 1
best = max(best, beyond - value)
```

`beyond - value` is the first run, the added value and the second run
together. If nothing was at `end + 2`, the second loop does not run and the
result is the first run plus one — which is "extend at the top", handled
without a branch.

"Extend at the bottom" is the same length, so it needs nothing. "Join to the
run below" is found when the run below is the one being walked.

## Still linear

Every run is walked once as the first run, and at most once more as the
second. Two passes over each value is `O(n)`.

The way to lose that is the way it was always lost: dropping the `value - 1
in present` check and starting a walk from everywhere. On one long run that
is quadratic, and the last test is one long run with a hole in it.

## Only one

`[1, 3, 5]` has two gaps and the answer is 3, not 5. The second walk starts
at `end + 2` and stops at the next missing value; it does not get to
continue past that one too. A version that keeps going "while the next value
or the one after is present" fills every gap it meets.

## What the twist was testing

Taking a solution apart far enough to see what it already knows at each
point. At the moment the first walk ends, the code holds a fact — *this
exact value is absent* — that the standard problem has no use for. The
follow-up is a question about that fact. A lot of "what if you could change
one thing" questions are answered at the place where the standard algorithm
stops.
