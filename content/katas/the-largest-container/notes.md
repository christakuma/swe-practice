# The Largest Container — a greedy move with a proof

Revealed after grading. The problem is the classic one (LeetCode 11); the
wording above is ours. It is the best short example of the difference between a
greedy rule that *works* and a greedy rule you can *justify* — and the
justification is three sentences, which is why it is worth doing.

## The move

Start at the widest container there is, and walk inward:

```python
low, high = 0, len(heights) - 1
best = 0
while low < high:
    best = max(best, min(heights[low], heights[high]) * (high - low))
    if heights[low] < heights[high]:
        low += 1
    else:
        high -= 1
return best
```

`O(n)` time, `O(1)` space, against `O(n²)` for comparing every pair.

## Why moving the shorter line is correct

Every move costs width, so the only decision is which end to give up. The
argument is short enough to hold in your head:

> A container's height is capped by the **shorter** of its two lines. So if you
> keep the shorter one and move the taller one inward, the height cannot rise —
> it is still capped by the line you kept — while the width has just fallen.
> Every such container is strictly worse than the one you just measured.

So moving the taller line can never help. Which means moving the shorter one is
the only move that can improve anything — and, the part that actually matters,
**discarding the shorter line is safe**:

> The best container involving that line is the one against the furthest
> remaining line, which is exactly the pair just measured. Nothing is lost by
> never considering it again.

That second claim is what makes this `O(n)` rather than a heuristic that passes
the tests. Each step eliminates a whole family of pairs *with an argument*. The
pointers meet after `n` steps, and every pair never evaluated has been proven
not to win.

**This is the distinction worth taking away.** A greedy algorithm is only
trustworthy when you can state what each step throws away and why it was
throwing away nothing. "Move the shorter pointer" is a rule; the two paragraphs
above are the reason you can ship it.

## The equal-heights case

Either move is correct, and the reason is the same argument applied twice:
whichever line you keep, the pair you are abandoning was already measured at
its maximum possible width. So no tie-break is needed — which is a relief,
because an unnecessary tie-break here would look load-bearing forever.

## Neither factor predicts the winner

The answer is a **product**, and the tests pin both directions on the same
shape of list:

- `[1, 1, 1, 9, 9]` → `9`. The two nines are adjacent; the widest pair is worth
  `min(1, 9) * 4 = 4`. Height wins.
- `[6, 1, 9, 9, 1, 6]` → `30`. The sixes at the ends are worth `6 * 5`, beating
  the adjacent nines at `9`. Width wins.

A solution that walks *toward* the tallest lines — a plausible-sounding greedy
inversion — settles for the tall adjacent pair and misses the wide one.
`test_does_not_stop_at_the_tallest_pair` uses `[90, 1, 100, 100, 1, 1, 1, 90]`,
where the answer is `630` from the outer nineties and the tempting pair is worth
`100`.

## Sorting is not available here

Worth saying explicitly, because it is the reflex from
[three sum](../three-sum-to-zero/notes.md): **you cannot sort this input.** The
area depends on the *distance between positions*, and sorting destroys
positions. This is a two-pointer problem that is not a sorted-data problem —
the pointers work because of the min-capping argument, not because of
monotonicity.

That is a useful pair to hold side by side. Three-sum's pointers move because
the data is ordered; this one's move because of a domination argument about the
objective function. Same mechanics, unrelated reasons.

## What to take away

**Two pointers converging from the ends is a technique for eliminating
candidates, and the technique is only as good as the elimination argument.**
When you reach for it, write down the sentence that says what the move
discards. If you cannot, you have a guess — and a guess that passes a handful
of examples is the most expensive kind of wrong answer, because it looks
finished.
