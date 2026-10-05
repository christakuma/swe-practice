# Rebuild a Tree From Traversals — two facts, one from each list

Revealed after grading. The problem is the classic one (LeetCode 105); the
wording above is ours. The reason it takes two traversals, and specifically
*these* two, is the interesting part — and it explains why distinct values are
in the specification rather than there for convenience.

## What each traversal knows

- **Pre-order names the root.** It is visited first, so the root is
  `preorder[0]`. It cannot tell you where the left subtree ends.
- **In-order locates the split.** The whole left subtree is visited before the
  root, so the root's position in `inorder` gives the left subtree's **size**.
  It cannot tell you which node is the root.

Neither alone is enough — one traversal is consistent with many trees. Together
they pin it exactly:

```python
position = {value: index for index, value in enumerate(inorder)}

def construct(pre_start, in_start, in_stop):
    if in_start > in_stop:
        return None
    value = preorder[pre_start]
    split = position[value]
    left_size = split - in_start
    return TreeNode(
        value,
        construct(pre_start + 1, in_start, split - 1),
        construct(pre_start + 1 + left_size, split + 1, in_stop),
    )
```

`left_size` is the only arithmetic, and it is the whole trick: computed from the
**in-order** split, then used to cut the **pre-order** range. The two
traversals disagree about order and agree about subtree sizes.

## Why distinct values is a requirement, not a convenience

With duplicates, `position[value]` is ambiguous — the root could be any of
several places in `inorder`, and different choices give different trees that
share both traversals. **The tree is genuinely not recoverable.** That is a fact
about the problem, not a limitation of the algorithm, and it is worth noticing
that the prompt's "all distinct" is doing load-bearing work rather than tidying
up.

Which pairs work at all is also not obvious: pre-order + in-order works,
post-order + in-order works, and **pre-order + post-order does not** — neither
locates the split, so a node with one child is ambiguous about which side it is
on. `test_distinguishes_a_left_child_from_a_right_child` is exactly that
ambiguity: both trees have pre-order `[1, 2]`, and only in-order separates them.

## Two ways to lose the linear bound

```python
split = inorder.index(value)                    # O(n) per node -> O(n^2)
```

Searching for the root on every call is the usual reason this comes out
quadratic. The dictionary is built once.

```python
left = construct(preorder[1:1 + size], inorder[:split])   # copies, O(n^2) again
```

Slicing is the natural way to say "the left part" and it copies — which
reintroduces exactly the cost the dictionary just removed. Index ranges carry
the same information for free.

**Both are the same mistake in different clothing: an operation that reads like
`O(1)` and is `O(n)`.** `list.index` and slicing are the two most common
offenders in Python, and in a recursion they turn a linear algorithm quadratic
without changing a line of the logic.

## Do not consume the input

```python
value = preorder.pop(0)      # tracks position by destroying the list
```

A popular way to avoid threading `pre_start` through the recursion. It mutates
the caller's list — and `pop(0)` is itself `O(n)`, so it manages to be both
rude and quadratic. `test_does_not_mutate_its_inputs` holds it.

## On verifying it

The reference was checked by round-tripping **every binary tree shape up to
eight nodes** — 2056 of them — through its own traversals.

That sweep is the test worth having, because the `left_size` arithmetic fails
at *particular shapes* rather than particular sizes. An off-by-one in the
pre-order cut is correct on balanced trees and wrong on one-sided ones, or vice
versa, and enumerating shapes is the only way to be sure which. The hand-picked
left-chain and right-chain cases are there to name the failure when the sweep
catches it.

## What to take away

**When a problem gives you two views of the same structure, work out what each
one uniquely knows.** Here it is "which node" and "how big", and the algorithm
is just those two facts applied recursively. The same question — what does this
input tell me that the other cannot? — is usually faster than trying to
manipulate both at once.
