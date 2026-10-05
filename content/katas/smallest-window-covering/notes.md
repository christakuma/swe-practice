# Smallest Window Covering — one integer instead of two tallies

Revealed after grading. The problem is the classic one (LeetCode 76); the
wording above is ours. It is the hardest sliding-window problem on the list,
and the difficulty is entirely in the bookkeeping — the window motion itself is
the same grow-and-shrink as every other one.

## The shape

Grow right until the window covers everything needed; shrink from the left
while it still covers; record; carry on. Each end moves forward at most `n`
times.

The question is how to answer **"does this window cover it?"** without
recomputing. Comparing two tallies is `O(k)` per step and makes the whole thing
`O(nk)`.

## One integer

`outstanding` = how many *required character slots* are still unfilled. The
window covers exactly when it hits zero. `O(1)` per step.

```python
for right, character in enumerate(text):
    if character in remaining:
        if remaining[character] > 0:
            outstanding -= 1
        remaining[character] -= 1

    while outstanding == 0:
        record(left, right)
        dropped = text[left]
        left += 1
        if dropped in remaining:
            remaining[dropped] += 1
            if remaining[dropped] > 0:
                outstanding += 1
```

Two details keep that integer honest, and they are the whole kata.

## Let the tally go negative

`remaining[c] < 0` means the window holds **more** copies of `c` than required.
That is not an error state to be clamped away — it is the only signal that
tells the shrink loop which leading character is safe to drop.

Clamp at zero and you lose the distinction between "exactly enough" and
"surplus", so the window cannot shrink past a character it does not need, and
the answer comes out too long. `test_shrinks_past_surplus_characters` uses
`"aaab"` needing `"ab"`: the answer is `"ab"`, and a clamped tally returns
`"aaab"`.

**A counter that can go negative is carrying two facts in one integer** — how
many are still needed, and how many are spare. That is worth recognising as a
deliberate encoding rather than sloppiness.

## Only decrement when the character was still needed

```python
if remaining[character] > 0:     # <- the guard
    outstanding -= 1
remaining[character] -= 1
```

Without the guard, a second `A` in a window needing one `A` satisfies the
requirement twice, `outstanding` reaches zero early, and a window that does not
cover gets reported as covering. `test_does_not_satisfy_a_requirement_twice`
uses `"AA"` against `"AB"`, where the answer is `""`.

The symmetric guard applies on the way out: `outstanding` goes back up only
when releasing a character takes its count back above zero — that is, when the
dropped copy was a *needed* one rather than a spare.

## Multiplicity is the whole specification

Covering `"aa"` needs **two** `a`s. Almost every wrong solution is wrong about
this: a `set` of required characters, a clamped tally, a double-decremented
counter. `test_requires_every_copy` and `test_covers_repeated_requirements`
pull in opposite directions, the way they do in
[three sum](../three-sum-to-zero/notes.md), and a solution has to satisfy both.

## Three wrong expectations, found by running them

Three of the expected values in this kata's suite were wrong when written —
including `smallest_window("aBb", "ab")`, written as `"Bb"`. The `B` is
uppercase and does not satisfy the lowercase requirement, so the window must
reach back to the real `a`: the answer is `"aBb"`.

The content suite caught it, and then every literal expectation in the file was
re-checked against the brute-force oracle programmatically. That is now a habit
across this batch rather than a one-off, and the reason is the same every time:
**for a problem whose answer depends on multiplicities and off-by-ones,
hand-computation is the wrong instrument.** Write the oracle, then let it mark
your homework.

## What to take away

**When a window predicate costs more than `O(1)`, find the scalar summary of
it.** The window motion is never the bottleneck in these problems — the
validity test is. Here `outstanding` is the summary, and keeping it correct
across both ends of the window is the real work.

And more generally: **a sliding window is cheap only if both the predicate and
its maintenance are incremental.** Grow-shrink with an `O(k)` check inside it
is a quadratic algorithm wearing a linear algorithm's clothes.
