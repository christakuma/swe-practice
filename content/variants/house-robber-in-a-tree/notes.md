# The state is still "was the last one taken?"

Revealed after grading. This is "House Robber III" (LeetCode 337).

The row version works because one fact about the past is enough to decide the
future: *was the previous house taken?* Two running numbers, one for each
answer.

A tree has no "previous". What it has is "below". The same single fact — *was
this subtree's root taken?* — is all a parent needs to know about a subtree,
so each call returns two numbers:

```python
taken = node.value + left_left + right_left
left  = max(left_taken, left_left) + max(right_taken, right_left)
```

## The line everyone gets wrong

```python
left = left_taken + right_taken        # wrong
```

"If I skip this node, I take its children." You *may*. You are not obliged
to, and in the chain `4, 1, 1, 4` the best answer skips two nodes running.
Skipping a node removes a constraint on its children; it does not add one.

## Why not levels

The obvious shortcut is to sum alternate levels and take the better half. It
fails for two reasons, and the tests have one of each:

- a chain `4, 1, 1, 4` wants levels 0 and 3;
- one branch may want its level 1 while its sibling branch wants level 2.

The choice is local to each subtree. Nothing ties a decision on the left
branch to a decision on the right, which is exactly why a recursion that
returns per-subtree answers works and a per-level sum does not.

## What the twist was testing

Whether the row solution was remembered as `max(prev1, prev2 + value)` or
understood as a two-state recurrence. The formula does not transplant onto a
tree; the states do. Returning a small tuple of "best under each condition
the caller might impose" is the general shape of dynamic programming on
trees.
