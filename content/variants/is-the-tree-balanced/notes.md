# One walk, two answers

Revealed after grading. This is "Balanced Binary Tree" (LeetCode 110).

The definition translates straight into code:

```python
def is_balanced(node):
    if node is None:
        return True
    return (abs(depth(node.left) - depth(node.right)) <= 1
            and is_balanced(node.left) and is_balanced(node.right))
```

It is correct. It also calls `depth` at every node, and each `depth` walks a
whole subtree — so a node `d` levels down is measured `d` times. On a chain
that is `O(n^2)`.

The fix is to notice that the recursion is already computing depths on its
way back up. It can report the verdict in the same breath:

```python
def depth(node):
    if node is None:
        return 0
    left, right = depth(node.left), depth(node.right)
    if UNBALANCED in (left, right) or abs(left - right) > 1:
        return UNBALANCED
    return 1 + max(left, right)
```

A depth is never negative, so `-1` is free to mean "something below here has
already failed". Every caller passes it up untouched.

## The three wrong definitions

- **Only the root.** Two chains of equal length under one root are level at
  the top and hopeless below it.
- **Leaf depths within one of each other.** A root with a two-node chain on
  one side and nothing on the other has all its leaves at the same depth. The
  empty side is a subtree of depth zero whether or not it has a leaf in it.
- **Node counts.** A full subtree of seven beside a subtree of two is
  balanced if their depths are 3 and 2.

## What the twist was testing

Bottom-up thinking. The standard problem returns one number from each
subtree. Most harder tree problems — this one, the best path sum, the
diameter, validating a search tree — are that same post-order walk returning
*a little more* than one number, so that the parent never has to go back and
look again.
