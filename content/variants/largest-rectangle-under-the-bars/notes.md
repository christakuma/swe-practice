# Ask each bar how far it can spread

Revealed after grading. This is "Largest Rectangle in Histogram"
(LeetCode 84).

The container problem, trapped rain water and this one share a picture and
have three different solutions, and the reason is what limits the height.

- **Container**: only the two end lines. Two pointers work.
- **Rain water**: the tallest bar to each side. Prefix maxima.
- **Rectangle**: the *shortest* bar anywhere in the span.

That last one kills the two-pointer walk. Moving in from the ends, you cannot
know what you are about to give up, because any bar in between can cap the
height.

## Change the question

Instead of choosing a span and finding its height, choose a **height** and
find its span. Every rectangle worth considering has height equal to some
bar, and extends from that bar outwards until it hits something shorter on
each side. So the problem is: *for every bar, find the nearest shorter bar to
the left and to the right.*

## The monotonic stack

Keep a stack of positions whose heights are non-decreasing. When a shorter
bar arrives:

```python
while rising and heights[rising[-1]] > height:
    tall = heights[rising.pop()]
    left = rising[-1] + 1 if rising else 0
    best = max(best, tall * (position - left))
```

For the bar just popped, the arriving bar is its nearest shorter bar on the
right, and the new top of the stack is its nearest shorter bar on the left —
everything between was taller and has already been popped. Both limits, one
pop.

Each position is pushed once and popped once: `O(n)` despite the nested
loop.

## Two details

- **Flush at the end.** Bars still on the stack never met a shorter bar;
  their rectangles run to the end of the list. Appending a 0 forces them
  out. Forgetting this gets every rising sequence wrong.
- **The width uses the new top, not the popped position.** `position -
  popped` ignores taller bars to the left that were popped earlier and that
  this rectangle also covers.

## What the twist was testing

Recognising that a familiar picture can hide an unfamiliar constraint. "Bars
and an area" triggers the two-pointer memory; asking *what actually bounds
the height* is what tells you it does not apply.
