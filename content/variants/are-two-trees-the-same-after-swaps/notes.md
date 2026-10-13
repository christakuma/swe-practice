# Two pairings, each of them whole

Revealed after grading. This is "Flip Equivalent Binary Trees" (LeetCode 951).

The standard problem compares left with left and right with right. A swap at a
node exchanges its subtrees, so here the children may also pair up crossed:

```python
straight = same(first.left, second.left) and same(first.right, second.right)
crossed = same(first.left, second.right) and same(first.right, second.left)
return straight or crossed
```

That is the whole change, and each node makes its own choice — which is what
separates this from a mirror image, where every node is swapped or none is.

## The bug this problem is known for

```python
return (same(a.left, b.left) or same(a.left, b.right)) and (
    same(a.right, b.left) or same(a.right, b.right)
)
```

It reads as "each of my children matches one of yours", and it lets both of
mine match the *same* one of yours. A node with children `2` and `2` against a
node with children `2` and `3` passes, because nobody has to be the `3`. A
pairing is a bijection: `or` between two complete pairings, `and` inside each.

With distinct values this never shows, because two children can never both
match one node — which is why the tests repeat values and LeetCode's do not.

## Another way to see it

Sort each node's children into a canonical order and compare the results. Two
trees are swap-equivalent exactly when their canonical forms are equal. That
is how the tests check the answer, and it is the better approach if you had to
group thousands of trees rather than compare two.

## What the twist was testing

That the base cases survived. Everything about `None` is unchanged — two
empty trees match, one empty tree does not — and the temptation, once the
problem has become "more forgiving", is to become forgiving there too.
