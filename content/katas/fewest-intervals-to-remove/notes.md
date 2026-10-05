# Fewest Intervals to Remove — sort by the end

Revealed after grading. The problem is the classic one (LeetCode 435); the
wording above is ours. It is **interval scheduling**, one of the few greedy
algorithms with a short exact proof, and the entire difficulty is one word in
the sort key.

## Flip the question first

"Remove the fewest" invites you to choose deletions, which means agonising over
each overlapping pair: *which of these two should go?* There is no local answer
to that.

"Keep the most" has no such problem. You consider intervals in some order and
ask only *can I take this next?* — a question with a yes/no answer and no
regret. Same problem, and one framing has a greedy algorithm while the other
does not.

**When a minimisation is awkward, try the complementary maximisation.** Here it
is the whole unlock, and `len(intervals) - kept` is the translation back.

## Sort by end, not by start

```python
ordered = sorted(intervals, key=lambda interval: interval[1])
kept, last_end = 0, None
for start, end in ordered:
    if last_end is None or start >= last_end:
        kept += 1
        last_end = end
return len(intervals) - kept
```

The proof is two sentences, and it is worth knowing because it is what makes
this greedy *correct* rather than plausible:

> Among the intervals you could take next, the one finishing earliest leaves
> the most room for everything after it. And it never costs anything: any
> optimal solution using a later-finishing interval can swap in the
> earliest-finishing one and stay valid, since it ends no later.

So the greedy choice is safe at every step — an **exchange argument**, the
standard way to establish that a greedy algorithm is optimal. Compare the
domination argument in
[the largest container](../the-largest-container/notes.md): both are "this step
discards nothing", which is what separates a greedy algorithm you can ship from
one that passes your examples.

## Why sorting by start fails

Sorting by start is the intuitive key. One long interval that starts first
blocks everything behind it, and a start-ordered scan takes it *because it got
there first*:

```
[(1, 100), (2, 3), (3, 4)]      by end: keep 2, remove 1
                                 by start: keep 1, remove 2

[(1, 10), (2, 3), (4, 5), (6, 7)]  by end: remove 1
                                    by start: remove 3
```

Both verified against the buggy variant. The second is the starker one and is
in the suite for that reason.

**The worked example in the prompt does not discriminate** —
`[(1, 2), (2, 3), (3, 4), (1, 3)]` gives 1 either way. That is noted in the
test docstring deliberately: developing against it would bless the wrong sort
key, which is the same hazard as the square matrices in
[read a matrix in spiral order](../read-a-matrix-in-spiral-order/notes.md).

## Touching is compatible here — and merges in the neighbouring kata

`start >= last_end`, not `>`. `(1, 2)` and `(2, 3)` share a point and do not
overlap, so both may stay.

Note this is the *same* endpoint convention as
[insert an interval](../insert-an-interval/notes.md) producing the *opposite*
behaviour: touching intervals **merge** when you are combining them and
**coexist** when you are packing them. The convention did not change; the
operation did. Carrying a comparison over from a neighbouring interval problem
is how this goes wrong.

Two identical zero-width intervals therefore need no removals at all: `(1, 1)`
and `(1, 1)` satisfy `start >= last_end`. Surprising, consistent, and worth
checking your intuition against rather than your memory.

## Two expected values that were wrong

`[(1, 3), (2, 4), (3, 5), (4, 6)]` was asserted as 1 removal and is 2 — the
staircase only supports `(1, 3)` and `(3, 5)`. And `[(1, 1), (1, 1)]` was
asserted as 1 and is 0, for the reason above.

Both caught by the content suite, then every literal in the file was
re-verified against the subset-enumerating oracle. By this point in the batch
that is simply the procedure: **hand-computed expectations for greedy interval
problems are not trustworthy**, because the thing you are likely to get wrong
is exactly the thing the kata is about.

## What to take away

**A greedy algorithm is a sort key plus a proof.** The loop is three lines and
nobody gets it wrong; the key is one word and decides correctness. When you
write one, state the exchange argument — if you cannot, you have not chosen a
key, you have guessed one.
