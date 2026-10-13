# Flip the report, not the traversal

Revealed after grading. This is "Binary Tree Zigzag Level Order Traversal"
(LeetCode 103).

The solution is the standard level-order traversal with one line changed:

```python
levels.append(level[::-1] if len(levels) % 2 else level)
```

That is all, and the reason this is a good interview follow-up is that the
*other* way of doing it looks just as natural and is wrong.

## The wrong way

"Read every other level right to left" suggests visiting the nodes right to
left: enqueue the right child before the left on alternate levels. But the
order nodes enter the queue is the order their *children* will be visited in.
Reverse it on level two and level three comes out as the children of 3
followed by the children of 2 — `6, 7, 4, 5` — which is neither direction.

The traversal has to stay left to right at every level. Only what is reported
flips.

## What the twist was testing

Whether you can tell the *mechanism* from the *output*. The queue is how the
tree is walked; the list of levels is what is returned. A requirement about
the second is almost never a reason to disturb the first, and the cheapest
correct change is usually the one made as late as possible.

(If the reversal bothers you, a deque filled from the left on odd levels does
the same thing without a second pass. It is still the report that changes.)
